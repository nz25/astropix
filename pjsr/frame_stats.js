/*
 * frame_stats.js -- contract 1: PixInsight's numbers for one frame.
 *
 * Opens a CFA frame, splits it into its four Bayer sub-planes with PI's own
 * SplitCFA, and reports simple statistics for the mosaic and for each plane,
 * plus PI's two noise estimators. It compares nothing; the comparison against
 * astropix is the notebook's, because the point of a referee is that it does
 * not know what answer we wanted (D6).
 *
 * Every value is PixInsight-normalised, in [0, 1]. Converting to ADC counts
 * is the caller's job and there is exactly one way to do it -- see
 * astropix.pixinsight.to_adc, and note that it is not a multiplication by
 * 4095.
 *
 * Job:    { "frame": "<absolute path, forward slashes>" }
 * Result: { core, frame, mosaic, planes: {cfa0..cfa3}, noise }
 */

#include "harness.jsh"

#feature-id    Astropix > Frame Statistics
#feature-info  Per-plane statistics and noise estimates for one CFA frame.

/*
 * The five numbers, for one image.
 *
 * `minimum` is here because it is the cheapest statistic a single displaced
 * pixel can move, and the CFA plane order is exactly the kind of error that
 * displaces pixels while leaving medians alone. `stdDev` divides by n-1 --
 * numpy divides by n -- so the comparison on our side carries ddof=1.
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
 * PI's own noise evaluation, chosen the way PI chooses it.
 *
 * NoiseEvaluation.js runs multiresolution support with decreasing layer
 * counts and accepts the first whose noisy-pixel set is at least 1% of the
 * frame, falling back to k-sigma only if none is. Both estimates are reported
 * whatever happens, because the interesting number here is not either one
 * alone -- it is where our clipped sigma sits between them.
 */
function noise( img )
{
   var out = { mrs: null, mrs_layers: null, mrs_count: null,
               ksigma: null, ksigma_count: null, chosen: null };
   var npx = img.width * img.height;

   for ( var layers = 4; layers >= 2; --layers )
   {
      var e = img.noiseMRS( layers );
      if ( out.mrs === null || e[1] > 0 )
      {
         out.mrs = e[0];
         out.mrs_layers = layers;
         out.mrs_count = e[1];
      }
      if ( e[1] >= 0.01*npx )
      {
         out.chosen = "mrs";
         break;
      }
   }

   var k = img.noiseKSigma();
   out.ksigma = k[0];
   out.ksigma_count = k[1];
   if ( out.chosen === null )
      out.chosen = "ksigma";
   return out;
}

report( function( job )
{
   if ( !job.frame )
      throw new Error( "job has no 'frame'" );

   var out = { core: coreInfo(), frame: { path: job.frame } };
   var windows = ImageWindow.open( job.frame );
   if ( windows.length < 1 )
      throw new Error( "ImageWindow.open returned nothing for " + job.frame );

   var win = windows[0];
   var opened = [ win ];
   try
   {
      var img = win.mainView.image;
      if ( img.numberOfChannels != 1 )
         throw new Error( "expected a single-channel mosaic, got "
                          + img.numberOfChannels + " channels; PixInsight "
                          + "debayered on load and the comparison is void" );
      out.frame.bits_per_sample = img.bitsPerSample;
      out.mosaic = describe( img );
      out.noise = { mosaic: noise( img ) };

      /*
       * SplitCFA writes its four outputs to new windows and reports their ids
       * in outputViewId0..3. Those properties are outputs, not inputs:
       * setting them before executeOn has no effect at all, which is a quiet
       * way to spend an afternoon.
       */
      var P = new SplitCFA;
      P.outputTree = false;
      P.outputSubDirectory = "";
      P.prefix = "astropix_cfa";
      P.postfix = "";
      P.overwrite = true;
      if ( !P.executeOn( win.mainView ) )
         throw new Error( "SplitCFA.executeOn returned false" );

      var ids = [ P.outputViewId0, P.outputViewId1,
                  P.outputViewId2, P.outputViewId3 ];
      out.planes = {};
      out.noise.planes = {};
      for ( var i = 0; i < 4; ++i )
      {
         if ( !ids[i] )
            throw new Error( "SplitCFA produced no outputViewId" + i );
         var w = ImageWindow.windowById( ids[i] );
         if ( w.isNull )
            throw new Error( "no window for view id " + ids[i] );
         opened.push( w );
         var key = "cfa" + i;
         out.planes[key] = describe( w.mainView.image );
         out.planes[key].view_id = ids[i];
         out.noise.planes[key] = noise( w.mainView.image );
      }
      return out;
   }
   finally
   {
      // forceClose on every window we opened, including on the failure path.
      // A modified window asked to close plainly puts up a save dialog, and
      // under --automation-mode that dialog is a hang with no diagnostic.
      for ( var j = 0; j < opened.length; ++j )
         try { opened[j].forceClose(); } catch ( e ) {}
   }
} );
