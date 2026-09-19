/*
 * harness.jsh -- the two things every script in this folder has to do.
 *
 * Read its parameters from a file, and report to a file. Both because
 * PixInsight is a GUI-subsystem binary with no console attached: console
 * output is invisible to whatever launched us, and command-line parameters
 * are unavailable (`-p=` raises a modal dialog that never gets clicked).
 * See pjsr/NOTES.md.
 *
 * A `.jsh` and not a `.js` on purpose: `pjsr/*.js` is the set of scripts that
 * must each write a result on both the success and the failure path, and
 * tests/test_pixinsight.py asserts exactly that over that glob. A header that
 * is never run directly should not be in it.
 */

#ifndef __ASTROPIX_HARNESS_jsh
#define __ASTROPIX_HARNESS_jsh

#define JOB_NAME    "job.json"
#define RESULT_NAME "result.json"

/*
 * The working directory is inherited from the launching process, and
 * astropix.pixinsight.run() gives every run its own. That is what lets a job
 * be found by name instead of by a path we would have had to be told -- and
 * what keeps two concurrent runs out of each other's files.
 */
function workPath( name )
{
   var dir = File.currentWorkingDirectory;
   if ( !dir || dir.length == 0 )
      throw new Error( "no working directory; cannot locate " + name );
   // charAt, not endsWith: PJSR is ECMAScript 5 and the ES6 string methods
   // are not reliably present across builds.
   if ( dir.charAt( dir.length - 1 ) != '/' )
      dir += '/';
   return dir + name;
}

function readJob()
{
   var path = workPath( JOB_NAME );
   if ( !File.exists( path ) )
      throw new Error( "no job file at " + path );
   return JSON.parse( File.readTextFile( path ) );
}

/*
 * Written with a File object rather than File.writeTextFile, which takes a
 * ByteArray in some builds -- and DataType_ByteArray is not defined in this
 * one, so the obvious idiom throws where it is least convenient.
 */
function writeResult( obj )
{
   var f = new File;
   f.createForWriting( workPath( RESULT_NAME ) );
   f.outTextLn( JSON.stringify( obj, null, 2 ) );
   f.close();
}

/*
 * Run `body`, and report either way.
 *
 * The failure path is the whole point. An exception that only reached the
 * console would leave the caller staring at a process that exited with
 * nothing to say, and the only way to find out where it died would be to
 * bisect the script. Written down, it arrives as {"ok": false, "error": ...}
 * in the file the caller is already reading.
 */
function report( body )
{
   var out;
   try
   {
      out = body( readJob() );
      out.ok = true;
   }
   catch ( e )
   {
      out = { ok: false, error: e.toString(), stack: (e.stack || "").toString() };
   }
   try
   {
      writeResult( out );
   }
   catch ( e2 )
   {
      // Last resort: if even the report cannot be written, say so where a
      // human running this in the GUI will see it.
      console.criticalln( "cannot write result file: " + e2.toString() );
      throw e2;
   }
}

/* The core's own identity, in every result. A number that came from a
 * different build is a different number. */
function coreInfo()
{
   return {
      version: format( "%d.%d.%d", CoreApplication.versionMajor,
                       CoreApplication.versionMinor,
                       CoreApplication.versionRelease ),
      build: CoreApplication.versionBuild,
      instance: CoreApplication.instance,
      working_directory: File.currentWorkingDirectory
   };
}

#endif
