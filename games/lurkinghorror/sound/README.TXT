
Hello sailor!

To play the Infocom game 'The Lurking Horror' with sound, you need the
following:

- DOS-PC with Soundblaster compatible sound board (note that old SBs
  can't control the volume)
- The Lurking Horror release 219 or release 221 (you can update release
  203, see below)
- Mark Howell's Zip version 2.04 (or my own interpreter "Frotz", should
  I ever finish it)
- The sound files contained in this marvellous package

First of all you need release 219 or release 221 of the 'Lurking Horror'
data file.  Probably your version is release 203; in this case run the
program UPDATELH from this package and follow the instructions.  In the
unlikely event that your edition of 'The Lurking Horror' is neither
release 219 nor release 221 nor release 203, please contact me:

    Stefan Jokisch,
    jokisch@ls7.informatik.uni-dortmund.de

Next you should go to the directory which you usually use for playing
The Lurking Horror and create a subdirectory SOUND.  Move all the SND
files from this package to that subdirectory.  As you can see, all the
sound files are called LURKINxx.SND.  If, for instance, you insist on
calling your data file HORROR.DAT, you would have to rename all the
sound files to HORRORxx.SND.  Obviously.

Third, make sure that the BLASTER environment variable is set.  Check
your AUTOEXEC.BAT file for a line similar to "SET BLASTER=A220 I7 D1".
In this example, 220 is the port address of your sound board, 7 is its
IRQ number and 1 is its DMA channel.  These values may differ for your
sound board; please refer to the documentation of your sound board for
more details.

Finally you should get hold of Zip 2.04.  It is available via anonymous
ftp from ftp.gmd.de at if-archive/infocom/interpreters/zip, the file is
called ZIP204.ZIP.  Read its "readme" file for further instructions.

Have fun!

