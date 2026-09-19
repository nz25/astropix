/*
 * probe.js -- does this installation answer us at all?
 *
 * The first script in this folder and the one to re-run after any PixInsight
 * upgrade. It measures nothing. It reports who answered, from where, and
 * whether a real frame opens, so that when a later script fails there is a
 * known-good baseline to fail against.
 *
 * Job:    { "frame": "<absolute path, forward slashes>" }  -- optional
 * Result: core identity, the job round-trip, and the frame's geometry.
 */

#include "harness.jsh"

#feature-id    Astropix > Probe
#feature-info  Reports core version, instance slot, working directory and \
               whether a frame opens.

report( function( job )
{
   var out = { core: coreInfo() };

   /*
    * The job round-trip, echoed back with its types. JSON is used here
    * precisely because the documented alternative -- parameters on the
    * command line -- delivers everything as a String, so a gain of 100 and a
    * gain of "100" would be indistinguishable on arrival. Echoing the types
    * is how that claim gets tested rather than believed.
    */
   out.echo = {};
   for ( var k in job )
      out.echo[k] = { value: job[k], type: typeof job[k] };

   out.frame_opened = false;
   if ( job.frame )
   {
      var windows = ImageWindow.open( job.frame );
      if ( windows.length < 1 )
         throw new Error( "ImageWindow.open returned nothing for " + job.frame );
      var win = windows[0];
      try
      {
         var img = win.mainView.image;
         out.frame_opened = true;
         out.frame = {
            path: job.frame,
            width: img.width,
            height: img.height,
            /*
             * Expected to be 1. PixInsight does not debayer a CFA frame on
             * load -- it opens the mosaic as a single-channel mono image,
             * which is the same array we read, and is what makes the whole
             * comparison like-for-like rather than a comparison against
             * interpolated pixels (D4).
             */
            channels: img.numberOfChannels,
            bits_per_sample: img.bitsPerSample,
            is_real: img.isReal,
            median: img.median()
         };
      }
      finally
      {
         // forceClose, not close: a plain close on a modified window asks to
         // save, and a question is a hang.
         win.forceClose();
      }
   }
   return out;
} );
