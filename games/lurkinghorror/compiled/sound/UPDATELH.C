/*
 * The Lurking Horror update
 *
 *	This is a small utility to update the Infocom game The Lurking
 *	Horror release 203 to release 221.  Written 1995 by Stefan
 *	Jokisch.
 *
 */

#include <stdio.h>

FILE *source = NULL;
FILE *conv = NULL;
FILE *dest = NULL;

char file_name[81];

int byte1 = 0;
int byte2 = 0;
int byte3 = 0;

long count = 0;

long source_file_size = 0x7fffffff;
long dest_file_size = 0x7fffffff;

/* The following should be 16-bit. */

unsigned source_checksum = 0;
unsigned dest_checksum = 0;
unsigned source_sum = 0;
unsigned dest_sum = 0;

int main(void)
{
    /*
     * Print some information and ask for the file name.
     */

    puts ("");
    puts ("The Lurking Horror update");
    puts ("");
    puts ("\tThis program updates the Infocom game 'The Lurking Horror'");
    puts ("\trelease 203 to release 221. The original data will be lost,");
    puts ("\tso make sure that you have made a backup copy!");
    puts ("");

    puts ("Type the name of the data file (eg lurking.dat):");
    gets (file_name);
    puts ("");

    /*
     * Open all files.
     */

    if ((source = fopen (file_name, "rb")) == NULL) {
	puts ("Cannot open data file!");
	goto emergency;
    }

    if ((conv = fopen ("lurking.cnv", "rb")) == NULL) {
	puts ("Cannot open lurking.cnv!");
	goto emergency;
    }

    if ((dest = fopen ("lurking.tmp", "wb")) == NULL) {
	puts ("Cannot open lurking.tmp!");
	goto emergency;
    }

    /*
     * Loop until the destination file is complete.
     */

    while (count < dest_file_size) {

	/* Read the data file. */

	byte1 = (count >= source_file_size) ? 0 : fgetc (source);

	if (byte1 == EOF) {
	    puts ("Error reading data file!");
	    goto emergency;
	}

	/* Read the conversion file. */

	byte2 = fgetc (conv);

	if (byte2 == EOF) {
	    puts ("Error reading lurking.cnv!");
	    goto emergency;
	}

	/* Calculate the destination file using EXOR. */

	byte3 = byte1 ^ byte2;

	if (count == 3 && byte1 != 203) {
	    puts ("Wrong version!");
	    goto emergency;
	}

	/* Read the file size entries. */

	if (count == 26) {
	    source_file_size = (long) byte1 << 9;
	    dest_file_size = (long) byte3 << 9;
	}

	if (count == 27) {
	    source_file_size |= byte1 << 1;
	    dest_file_size |= byte3 << 1;
	}

	/* Read the checksum entries. */

	if (count == 28) {
	    source_checksum = byte1 << 8;
	    dest_checksum = byte3 << 8;
	}

	if (count == 29) {
	    source_checksum |= byte1;
	    dest_checksum |= byte3;
	}

	/* Sum up all bytes starting at $40. */

	if (count >= 64) {
	    source_sum += byte1;
	    dest_sum += byte3;
	}

	/* Write the destination file. */

	if (fputc (byte3, dest) == EOF) {
	    puts ("Error writing lurking.tmp!");
	    goto emergency;
	}

	count++;
    }

    /*
     * Validate checksums.
     */

    if (source_sum != source_checksum || dest_sum != dest_checksum) {
	puts ("Checksum error!");
	goto emergency;
    }

    /*
     * Close all files.
     */

    fclose (source);
    fclose (conv);
    fclose (dest);

    /*
     * Replace the old data file by the new data file.
     */

    if (remove (file_name)) {
	puts ("Cannot delete data file! (new data file is lurking.tmp)");
	return (0);
    }

    if (rename ("lurking.tmp", file_name)) {
	puts ("Cannot rename lurking.tmp! (new data file is lurking.tmp)");
	return (0);
    }

    puts ("Done!");

    return (0);

emergency:

    /*
     * Panic! Close all open files and exit.
     */

    if (source != NULL)
	fclose (source);
    if (conv != NULL)
	fclose (conv);
    if (dest != NULL)
	fclose (dest);

    if (dest != NULL)
	remove ("lurking.tmp");

   return (1);
}

