/*
 * register.js -- contract 3: put every light on one grid without debayering.
 *
 * The split approach. Each CFA frame is cut into its four Bayer sub-planes with
 * SplitCFA, and each plane is registered on its own, against the same plane of
 * one shared reference frame. Nothing is ever interpolated *across* colours, so
 * the rule every number in this project obeys -- noise statistics on the CFA
 * sub-planes, never on a debayered image -- survives registration intact. What
 * registration does interpolate is *within* a plane, onto a grid shifted by the
 * dither, and that resampling is exactly the cost contract 3 exists to measure.
 *
 * One reference for every frame of every cell, deliberately. The four cells of
 * the sky-pair night are compared in a fixed signal ROI, and a ROI only means
 * the same patch of sky in every cell if every cell was resampled onto the same
 * grid. The reference frame itself is split and written but never resampled,
 * so a caller must leave it out of any stack: it is the one frame whose noise
 * the kernel never touched.
 *
 * Plane names are this project's, not PixInsight's index: SplitCFA returns
 * R, G2, G1, B, with the greens transposed against a naive reading of RGGB
 * (NOTES.md section 6), and the mapping is applied here once.
 *
 * The split planes are temporary and deleted once their plane is registered.
 * Only the registered planes are kept, as 16-bit XISF in stored units -- the
 * interpolated value is kept to 1/16 of an ADC count, which is far below any
 * noise this measures.
 *
 * Job:    { "reference": path, "frames": [ { "path": ..., "stem": ... } ],
 *           "outdir": path with split/, reg/ and ref/ already inside it,
 *           "interpolation": "lanczos3" | "auto" }
 * Result: { core, reference, settings, frames: [ { stem, planes: {R: {...}} } ] }
 */

#include "harness.jsh"

#feature-id    Astropix > Register
#feature-info  Split CFA frames into sub-planes and register each plane.

#define PLANES_PI [ "R", "G2", "G1", "B" ]

/*
 * StarAlignment's outputData row, named. Indices read off a probe run on a
 * session 06 light (2026-09-26): the output path, the mask path, the match
 * count, then the model's quality figures, then the 3x3 homography row by row.
 * Everything after the homography is star coordinates, which nothing here reads
 * and which would make the result file megabytes long.
 */
var ALIGN_FIELDS = [ "output", "mask", "matches", "inliers", "overlapping",
                     "regularity", "quality", "rms_error", "rms_error_dev",
                     "peak_error_x", "peak_error_y",
                     "H11", "H12", "H13", "H21", "H22", "H23", "H31", "H32", "H33" ];

function named( row )
{
   var out = {};
   for ( var i = 0; i < ALIGN_FIELDS.length; ++i )
      out[ALIGN_FIELDS[i]] = row[i];
   return out;
}

/*
 * The caller creates the directories. PixInsight cannot create one on a UNC
 * path -- `File.createDirectory` walks up to "//ds1513" and fails with Win32
 * error 161 -- and the intermediates live on the NAS by design (D98).
 */
function ensureDir( d )
{
   if ( !File.directoryExists( d ) )
      throw new Error( "no directory " + d + "; the caller creates it" );
}

/* One CFA frame into four plane files. Returns name -> path. */
function splitTo( path, dir, stem )
{
   var ws = ImageWindow.open( path );
   if ( !ws || ws.length < 1 || ws[0].isNull )
      throw new Error( "cannot open " + path );
   var win = ws[0];
   var opened = [ win ];
   try
   {
      if ( win.mainView.image.numberOfChannels != 1 )
         throw new Error( path + " is not a single-channel CFA frame" );
      var P = new SplitCFA;
      P.outputTree = false;
      P.outputSubDirectory = "";
      P.prefix = "astropix_cfa";
      P.postfix = "";
      P.overwrite = true;
      if ( !P.executeOn( win.mainView ) )
         throw new Error( "SplitCFA.executeOn returned false on " + path );
      var ids = [ P.outputViewId0, P.outputViewId1, P.outputViewId2, P.outputViewId3 ];
      var names = PLANES_PI;
      var out = {};
      for ( var i = 0; i < 4; ++i )
      {
         var w = ImageWindow.windowById( ids[i] );
         if ( w.isNull )
            throw new Error( "no window for SplitCFA output " + ids[i] );
         opened.push( w );
         var f = dir + "/" + stem + "_" + names[i] + ".fits";
         if ( !w.saveAs( f, false, false, false, false ) )
            throw new Error( "could not write " + f );
         out[names[i]] = f;
      }
      return out;
   }
   finally
   {
      // forceClose, never close: a modified window asked to close plainly
      // raises a save dialog, and under --automation-mode that is a hang.
      for ( var j = 0; j < opened.length; ++j )
         try { opened[j].forceClose(); } catch ( e ) {}
   }
}

function interpolationOf( name )
{
   if ( name == "auto" )
      return StarAlignment.prototype.Auto;
   if ( name == "lanczos3" || name === undefined )
      return StarAlignment.prototype.Lanczos3;
   throw new Error( "unknown interpolation '" + name + "'" );
}

report( function( job )
{
   if ( !job.frames || !job.frames.length )
      throw new Error( "job has no frames" );
   var root = job.outdir;
   var splitDir = root + "/split", regDir = root + "/reg", refDir = root + "/ref";
   ensureDir( splitDir ); ensureDir( regDir ); ensureDir( refDir );

   var out = { core: coreInfo(), reference: job.reference, frames: [] };
   var t0 = Date.now();
   var ref = splitTo( job.reference, refDir, "ref" );

   var split = [];
   for ( var i = 0; i < job.frames.length; ++i )
      split.push( splitTo( job.frames[i].path, splitDir, job.frames[i].stem ) );
   out.split_s = (Date.now() - t0)/1000;

   for ( var i = 0; i < job.frames.length; ++i )
      out.frames.push( { stem: job.frames[i].stem, path: job.frames[i].path, planes: {} } );

   var names = PLANES_PI;
   for ( var k = 0; k < 4; ++k )
   {
      var name = names[k];
      var P = new StarAlignment;
      P.referenceImage = ref[name];
      P.referenceIsFile = true;
      var targets = [];
      for ( var i = 0; i < split.length; ++i )
         targets.push( [ true, true, split[i][name] ] );
      P.targets = targets;
      P.outputDirectory = regDir;
      /*
       * No `outputExtension`: this build writes XISF whatever it is given,
       * so asking for FITS would only make the job say something the files
       * do not. astropix.fits.read_xisf reads them.
       */
      P.outputPostfix = "_r";
      P.overwriteExistingFiles = true;
      P.generateDrizzleData = false;
      // A dithered, guided field over a few hours is a similarity transform
      // to well under a pixel; a distortion model would fit noise.
      P.distortionCorrection = false;
      P.pixelInterpolation = interpolationOf( job.interpolation );
      P.executeGlobal();

      /*
       * Per frame, never per batch. StarAlignment does not stop on a frame it
       * cannot solve; it skips it and carries on, so a batch-level `true`
       * says nothing about any one frame. A frame that failed has an empty
       * output path, and it is reported as such rather than dropped.
       */
      var od = P.outputData;
      for ( var i = 0; i < split.length; ++i )
      {
         var rec = (od && i < od.length) ? named( od[i] ) : { output: "" };
         rec.ok = !!rec.output && File.exists( rec.output );
         out.frames[i].planes[name] = rec;
         try { File.remove( split[i][name] ); } catch ( e ) {}
      }
      if ( k == 0 )
         out.settings = {
            interpolation: P.pixelInterpolation,
            clamping_threshold: P.clampingThreshold,
            distortion_correction: P.distortionCorrection
         };
   }
   out.total_s = (Date.now() - t0)/1000;
   return out;
} );
