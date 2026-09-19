/*
 * integrate.js -- contract 2: what a stack is actually worth.
 *
 * Integrates a list of frames with ImageIntegration and reports the result's
 * statistics, PI's noise estimates for it, and every setting that produced
 * it. It computes no efficiency and compares nothing: `eta_comb` is the
 * notebook's arithmetic over this number and the single-frame number, because
 * a referee that knew which answer was wanted would not be one (D6).
 *
 * **The settings are reported because `eta_comb` is not independent of them.**
 * MISSION requires its provenance to record the stack size and the rejection
 * settings, and the only trustworthy source for what a run actually used is
 * the run itself -- a job file records what was asked for, which is a
 * different thing whenever a process silently declines. So every field below
 * is read back off the process instance *after* execution.
 *
 * No registration happens here, deliberately. A stack of unregistered frames
 * leaves out the one term guaranteed to cost something -- resampling a
 * dithered frame onto a common grid -- so the efficiency measured from it is
 * an upper bound by construction, and the gap to the registered number is the
 * resampling loss.
 *
 * Job:    { "frames": [absolute paths, forward slashes],
 *           "combination": "average" | "median",
 *           "rejection": "none" | "sigma" | "winsorized" | "percentile",
 *           "normalization": "none" | "additive" | "additive_scaling",
 *           "weight_mode": "dont_care" | "psf_signal" | "noise",
 *           "sigma_low", "sigma_high": numbers }
 * Result: { core, frames, settings, integrated, noise }
 */

#include "harness.jsh"

#feature-id    Astropix > Integrate
#feature-info  Integrate a list of frames and report the result and its settings.

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
 * PI's own noise evaluation, the way contract 1 asks for it, so that a stack
 * and a single frame are judged by the same instrument. Contract 1 found our
 * 1.4826*MAD sitting on a grid of 1.4826 ADC counts and reading high wherever
 * the spread is a few counts -- which is exactly where an integrated frame
 * lives, so MRS is the estimator that matters here and `std` is context.
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

function combinationOf( name )
{
   if ( name == "median" )
      return ImageIntegration.prototype.Median;
   if ( name == "average" || name === undefined )
      return ImageIntegration.prototype.Average;
   throw new Error( "unknown combination '" + name + "'" );
}

function rejectionOf( name )
{
   if ( name == "none" || name === undefined )
      return ImageIntegration.prototype.NoRejection;
   if ( name == "sigma" )
      return ImageIntegration.prototype.SigmaClip;
   if ( name == "winsorized" )
      return ImageIntegration.prototype.WinsorizedSigmaClip;
   if ( name == "percentile" )
      return ImageIntegration.prototype.PercentileClip;
   throw new Error( "unknown rejection '" + name + "'" );
}

/*
 * How frames are weighted against each other, and why this cannot be left
 * to the default.
 *
 * `weightMode` defaults to **7, PSF Signal Weight**: each frame is weighted
 * by the signal of the stars detected in it. On a star field that is the
 * right instrument. On anything without stars -- a bias, a dark, a flat, or
 * the synthetic frames this contract is checked with -- there are no valid
 * PSF samples, the weight comes out zero, and `executeGlobal()` returns a
 * bare `false` with "Zero or insignificant PSF Signal Weight estimate" in a
 * log the caller cannot see unless it asks.
 *
 * So the weighting is always stated, never inherited. `dont_care` gives every
 * frame equal weight, which is what an efficiency measurement wants in any
 * case: `eta_comb` against the ideal `sqrt(N)` is defined on equally weighted
 * frames, and unequal weighting is one of the things it is measuring the cost
 * of rather than something it should have applied to itself.
 */
function weightModeOf( name )
{
   if ( name == "dont_care" || name === undefined )
      return ImageIntegration.prototype.DontCare;
   if ( name == "psf_signal" )
      return 7;
   if ( name == "noise" )
      return ImageIntegration.prototype.NoiseEvaluation;
   throw new Error( "unknown weight_mode '" + name + "'; expected "
                    + "dont_care, psf_signal or noise" );
}

function normalizationOf( name )
{
   if ( name == "none" )
      return ImageIntegration.prototype.NoNormalization;
   if ( name == "additive" )
      return ImageIntegration.prototype.Additive;
   if ( name == "additive_scaling" || name === undefined )
      return ImageIntegration.prototype.AdditiveWithScaling;
   throw new Error( "unknown normalization '" + name + "'" );
}

/*
 * One integration: run it, and report the result beside the settings that
 * produced it.
 */
function runOne( spec )
{
   /*
    * Three, not two. ImageIntegration refuses a global execution with fewer
    * than three source images -- "This instance of ImageIntegration defines
    * less than three source images" -- whatever the rejection setting is, so
    * the bottom rung of a doubling ladder is simply unavailable through this
    * engine. Checked here rather than left to the process, so the message
    * says what to do about it.
    */
   if ( !spec.frames || spec.frames.length < 3 )
      throw new Error( "a run needs 'frames', at least three of them: "
                       + "ImageIntegration refuses fewer, so an N=2 rung "
                       + "cannot be measured this way" );

   var run = { label: spec.label || null, n: spec.frames.length };
   var P = new ImageIntegration;
   var rows = [];
   for ( var i = 0; i < spec.frames.length; ++i )
      rows.push( [ true, spec.frames[i], "", "" ] );
   P.images = rows;
   P.combination = combinationOf( spec.combination );
   P.rejection = rejectionOf( spec.rejection );
   P.normalization = normalizationOf( spec.normalization );
   P.weightMode = weightModeOf( spec.weight_mode );
   /*
    * PSF signal evaluation runs even when nothing weights by it, and on a
    * frame without stars it warns on every file. Off unless something asks.
    */
   P.evaluateSNR = (spec.evaluate_snr === undefined) ? false : spec.evaluate_snr;
   if ( spec.sigma_low !== undefined )
      P.sigmaLow = spec.sigma_low;
   if ( spec.sigma_high !== undefined )
      P.sigmaHigh = spec.sigma_high;
   // Rejection maps are windows we would only have to close again, and
   // nothing here reads them.
   P.generateRejectionMaps = false;
   P.generateIntegratedImage = true;
   /*
    * The cache is off, and that is not a performance choice.  A ladder asks
    * for the *same* file paths under different settings, one run after
    * another, which is precisely the shape a cache keyed on inputs gets
    * wrong.  A stale hit would return a previous arm's numbers wearing this
    * arm's settings, and nothing downstream could tell.
    */
   P.useCache = (spec.use_cache === undefined) ? false : spec.use_cache;

   if ( !P.executeGlobal() )
      throw new Error( "ImageIntegration.executeGlobal returned false" );

   /*
    * Read back off the instance, not off the job.  What a process was asked
    * to do and what it did are the same thing right up until they are not,
    * and `eta_comb`'s provenance cannot rest on the former.
    */
   run.settings = {
      requested: { combination: spec.combination, rejection: spec.rejection,
                   normalization: spec.normalization,
                   weight_mode: spec.weight_mode,
                   sigma_low: spec.sigma_low, sigma_high: spec.sigma_high },
      combination: P.combination,
      rejection: P.rejection,
      normalization: P.normalization,
      rejection_normalization: P.rejectionNormalization,
      weight_mode: P.weightMode,
      sigma_low: P.sigmaLow,
      sigma_high: P.sigmaHigh,
      clip_low: P.clipLow,
      clip_high: P.clipHigh,
      n_images: rows.length
   };

   var w = ImageWindow.windowById( P.integrationImageId );
   if ( w.isNull )
      throw new Error( "no window for integrationImageId '"
                       + P.integrationImageId + "'" );
   try
   {
      var img = w.mainView.image;
      if ( img.numberOfChannels != 1 )
         throw new Error( "expected a single-channel result, got "
                          + img.numberOfChannels + " channels" );
      run.integrated = describe( img );
      run.integrated.view_id = P.integrationImageId;
      run.integrated.bits_per_sample = img.bitsPerSample;
      run.integrated.is_real = img.isReal;
      run.noise = noise( img );
   }
   finally
   {
      try { w.forceClose(); } catch ( e ) {}
   }
   return run;
}

report( function( job )
{
   /*
    * Every rung in one launch, for the reason contract 1 already established:
    * core startup is about forty seconds and dominates everything a ladder
    * actually does.
    */
   var runs = job.runs;
   if ( !runs || !runs.length )
      runs = [ { frames: job.frames, combination: job.combination,
                 rejection: job.rejection, normalization: job.normalization,
                 sigma_low: job.sigma_low, sigma_high: job.sigma_high } ];

   /*
    * Each run reports its own outcome rather than throwing the batch away.
    * A rung that a process declines is a *finding* about that setting -- the
    * three-image floor below was found exactly this way -- and losing eight
    * good rungs to it would mean another launch to learn the same thing. The
    * top level stays ok; a caller that wants a clean ladder checks `ok` on
    * every run, and the notebook that reads this does.
    */
   var out = { core: coreInfo(), runs: [] };
   for ( var i = 0; i < runs.length; ++i )
   {
      try
      {
         var r = runOne( runs[i] );
         r.ok = true;
         out.runs.push( r );
      }
      catch ( e )
      {
         out.runs.push( { ok: false, label: runs[i].label || null,
                          n: runs[i].frames ? runs[i].frames.length : 0,
                          requested: { combination: runs[i].combination,
                                       rejection: runs[i].rejection,
                                       normalization: runs[i].normalization },
                          error: e.toString() } );
      }
   }
   return out;
} );
