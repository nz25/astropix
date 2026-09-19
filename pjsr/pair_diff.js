/*
 * pair_diff.js -- contract 2: what PixelMath does to a difference.
 *
 * Opens two frames, computes `a - b + pedestal` with PixelMath, and reports
 * statistics of the result. It decides nothing: the sample format, the
 * pedestal and the truncation flag all arrive in the job, and the script
 * reports what it was told to do alongside what came out. A referee that
 * chose the safe settings itself could never demonstrate the unsafe ones,
 * and demonstrating them is the point (L23).
 *
 * The defaults of the process are the trap, which is why they are worth
 * writing down. `PixelMath.truncate` is **true** and `newImageSampleFormat`
 * is **SameAsTarget** in a fresh instance, so the obvious way to subtract two
 * 16-bit frames clips every negative difference at zero. A difference of two
 * frames from the same distribution is centred on zero and is therefore
 * negative half the time, so what survives is a half-normal and its standard
 * deviation is smaller by a factor that looks entirely plausible on a real
 * bias pair. Nothing downstream can detect it.
 *
 * Every value reported is PixInsight-normalised, in [0, 1]. Converting is the
 * caller's job -- astropix.pixinsight.to_adc, and it is not a multiply by 4095.
 *
 * Job:    { "a", "b": absolute paths, forward slashes
 *           "pedestal": number added after the subtraction
 *           "sample_format": "f32" | "i16" | "same"
 *           "truncate": bool }
 * Result: { core, inputs, settings, diff, noise }
 */

#include "harness.jsh"

#feature-id    Astropix > Pair Difference
#feature-info  Difference of two frames under stated PixelMath settings.

#define A_ID "astropix_pair_a"
#define B_ID "astropix_pair_b"
#define D_ID "astropix_pair_diff"

/*
 * Same five numbers as contract 1, so the two contracts are read in the same
 * units and with the same estimators. `stdDev` divides by n-1.
 */
function describe( img )
{
   return {
      width: img.width,
      height: img.height,
      n: img.width * img.height,
      min: img.minimum(),
      max: img.maximum(),
      mean: img.mean(),
      median: img.median(),
      std: img.stdDev(),
      mad: img.MAD()
   };
}

/*
 * Where the pixels sit relative to the container's bounds.
 *
 * This is what makes the trap visible without knowing the injected sigma, and
 * the distinction that earns its keep is **below zero** against **exactly
 * zero**. They are the same pixels in both arms and they mean opposite
 * things: a difference that keeps its negative half is intact, and one that
 * has piled that same half onto exactly 0.0 has been clipped. `std` alone
 * cannot tell those apart -- it just reads low, plausibly. A census can.
 *
 * Counting is per pixel through `sample()`, which is fine on the small
 * synthetic frames this contract is checked with and slow on a full mosaic.
 * That is the right way round: the census is evidence about the arithmetic,
 * and the arithmetic does not know how big the frame is.
 */
function census( img )
{
   var n = img.width * img.height;
   var below = 0, at0 = 0, at1 = 0, above = 0;
   for ( var y = 0; y < img.height; ++y )
      for ( var x = 0; x < img.width; ++x )
      {
         var v = img.sample( x, y );
         if ( v < 0.0 )
            ++below;
         else if ( v == 0.0 )
            ++at0;
         else if ( v > 1.0 )
            ++above;
         else if ( v == 1.0 )
            ++at1;
      }
   return { n: n, below_zero: below, at_zero: at0,
            at_one: at1, above_one: above,
            frac_below_zero: below/n, frac_at_zero: at0/n,
            frac_at_one: at1/n, frac_above_one: above/n };
}

function sampleFormat( name )
{
   if ( name == "f32" || name === undefined )
      return PixelMath.prototype.f32;
   if ( name == "i16" )
      return PixelMath.prototype.i16;
   if ( name == "same" )
      return PixelMath.prototype.SameAsTarget;
   throw new Error( "unknown sample_format '" + name + "'; "
                    + "expected f32, i16 or same" );
}

function openAs( path, id, opened )
{
   var windows = ImageWindow.open( path );
   if ( windows.length < 1 )
      throw new Error( "ImageWindow.open returned nothing for " + path );
   var w = windows[0];
   opened.push( w );
   w.mainView.id = id;
   return w;
}

/*
 * One arm: subtract under one set of settings and report what came out.
 *
 * `opened` is the caller's list so that a throw half way through still closes
 * every window -- a modified window asked to close plainly raises a save
 * dialog, and under --automation-mode a dialog is a hang with no diagnostic.
 */
function runArm( wa, spec, opened )
{
   var pedestal = (spec.pedestal === undefined) ? 0.5 : spec.pedestal;
   var truncate = (spec.truncate === undefined) ? false : spec.truncate;
   var fmtName = (spec.sample_format === undefined) ? "f32" : spec.sample_format;

   var arm = { label: spec.label || null,
               settings: { pedestal: pedestal, truncate: truncate,
                           sample_format: fmtName } };

   var P = new PixelMath;
   P.expression = A_ID + " - " + B_ID + " + " + pedestal;
   P.useSingleExpression = true;
   P.createNewImage = true;
   P.newImageId = D_ID;
   P.newImageWidth = 0;
   P.newImageHeight = 0;
   P.newImageAlpha = false;
   P.newImageColorSpace = PixelMath.prototype.Gray;
   P.newImageSampleFormat = sampleFormat( fmtName );
   // Rescale is a different hazard from truncation and is off in every arm:
   // it would map the result's own range onto [0, 1] and change the standard
   // deviation by a factor nobody asked for.
   P.rescale = false;
   P.truncate = truncate;
   P.truncateLower = 0;
   P.truncateUpper = 1;
   arm.settings.expression = P.expression;

   if ( !P.executeOn( wa.mainView ) )
      throw new Error( "PixelMath.executeOn returned false" );

   var wd = ImageWindow.windowById( D_ID );
   if ( wd.isNull )
      throw new Error( "PixelMath produced no window '" + D_ID + "'" );
   opened.push( wd );
   try
   {
      var img = wd.mainView.image;
      arm.diff = describe( img );
      // What the format request actually produced, rather than what was asked
      // for.  A silently ignored sample format would make the whole
      // comparison meaningless while every number still looked reasonable.
      arm.diff.bits_per_sample = img.bitsPerSample;
      arm.diff.is_real = img.isReal;
      arm.census = census( img );
      arm.noise = { ksigma: img.noiseKSigma()[0] };
   }
   finally
   {
      // Closed inside the loop, not at the end: every arm writes to the same
      // view id, and a leftover window would make the next arm's
      // `windowById` find the previous arm's result.
      opened.pop();
      try { wd.forceClose(); } catch ( e ) {}
   }
   return arm;
}

report( function( job )
{
   if ( !job.a || !job.b )
      throw new Error( "job needs 'a' and 'b'" );

   /*
    * Every arm in one launch.  A launch costs about forty seconds of core
    * startup and the subtraction itself costs milliseconds, so a script that
    * can do eight settings in one run should -- the alternative is five
    * minutes of PixInsight starting up to answer one question eight times.
    */
   var arms = job.arms;
   if ( !arms || !arms.length )
      arms = [ { pedestal: job.pedestal, truncate: job.truncate,
                 sample_format: job.sample_format } ];

   var out = { core: coreInfo(), inputs: { a: job.a, b: job.b } };
   var opened = [];
   try
   {
      var wa = openAs( job.a, A_ID, opened );
      var wb = openAs( job.b, B_ID, opened );

      var ia = wa.mainView.image, ib = wb.mainView.image;
      if ( ia.numberOfChannels != 1 || ib.numberOfChannels != 1 )
         throw new Error( "expected single-channel mosaics; PixInsight "
                          + "debayered on load and the comparison is void" );
      if ( ia.width != ib.width || ia.height != ib.height )
         throw new Error( "frames differ in size" );
      out.inputs.a_stats = describe( ia );
      out.inputs.b_stats = describe( ib );
      out.inputs.bits_per_sample = ia.bitsPerSample;

      out.arms = [];
      for ( var i = 0; i < arms.length; ++i )
         out.arms.push( runArm( wa, arms[i], opened ) );
      return out;
   }
   finally
   {
      for ( var j = 0; j < opened.length; ++j )
         try { opened[j].forceClose(); } catch ( e ) {}
   }
} );
