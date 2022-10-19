# Voxseg-ELAN 0.1.1

Voxseg-ELAN integrates the voice activity detection methods offered by
[Voxseg](https://github.com/NickWilkinson37/voxseg) ([Wilkinson &
Niesler 2021](https://arxiv.org/abs/2103.03529)) into 
[ELAN](https://tla.mpi.nl/tools/tla-tools/elan/), allowing users to apply
voice activity detection to multimedia sources linked to ELAN transcripts
directly from within ELAN's user interface.

## Requirements and installation

Voxseg-ELAN makes use of several of other open-source applications and
utilities:

* [ELAN](https://tla.mpi.nl/tools/tla-tools/elan/) (tested with ELAN 6.3
  and 6.4 under macOS 12.6)
* [Python 3](https://www.python.org/) (tested with Python 3.9)
* [ffmpeg](https://ffmpeg.org)

Voxseg-ELAN is written in Python 3, and also depends on the following
Python packages, all of which should be installed in a virtual environment:

* [Voxseg](https://github.com/NickWilkinson37/voxseg), installed with all
   of its dependencies. This can be done with `pip` and a clone of the
   current Voxseg GitHub repository.
* [pydub](https://github.com/jiaaro/pydub), installed in the same
   virtual environment as Voxseg (tested with v0.25.1)
* [tensorflow](https://pypi.org/project/tensorflow/), installed in
   the same virtual environment as Voxseg and pydub (tested with v2.10.0).

Under macOS 12.6, the following commands can be used to fetch and install the
necessary Python packages:
```
git clone https://github.com/coxchristopher/voxseg-elan
cd voxseg-elan

python3 -m virtualenv venv-voxseg
source venv-voxseg/bin/activate

git clone https://github.com/NickWilkinson37/voxseg.git
pip install ./voxseg
pip install pydub tensorflow
```
  
Once all of these tools and packages have been installed, Voxseg-ELAN can
be made available to ELAN as follows:

1. Edit the file `voxseg-elan.sh` to specify (a) the directory in
   which ffmpeg is located, and (b) a Unicode-friendly language and
   locale (if `en_US.UTF-8` isn't available on your computer).
2. To make Voxseg-ELAN available to ELAN, move your Voxseg-ELAN directory
   into ELAN's `extensions` directory.  This directory is found in different
   places under different operating systems:
   
   * Under macOS, right-click on `ELAN_6.4` in your `/Applications`
     folder and select "Show Package Contents", then copy your `Voxseg-ELAN`
     folder into `ELAN_6.4.app/Contents/app/extensions`.
   * Under Linux, copy your `Voxseg-ELAN` folder into `ELAN_6-4/app/extensions`.
   * Under Windows, copy your `Voxseg-ELAN` folder into `C:\Users\AppData\Local\ELAN_6-4\app\extensions`.

Once ELAN is restarted, it will now include 'Voxseg voice activity detection'
in the list of Recognizers found under the 'Recognizer' tab in Annotation Mode.
The user interface for this recognizer allows users to enter the settings needed
to apply voice activity detection to a selected WAV audio recording that hasx
been linked to this ELAN transcript.  Additional settings (e.g., the speech vs.
non-speech threshold, constant adjustments to the start and end-times of 
recognized speech segments, etc.) can be configured through the recognizer
interface, as well.

Once these settings have been entered in Voxseg-ELAN, pressing the `Start`
button will begin applying Voxseg's voice activity detection to the selected
audio recording.  Once that process is complete, if no errors occurred, ELAN
will allow the user to load the resulting tier with the automatically
recognized speech segments into the current transcript.

## Limitations

This is an alpha release of Voxseg-ELAN, and has only been tested under macOS
(12.6) with Python 3.9.  No support for Windows or Linux is included in this
version.

## Acknowledgements

Thanks are due to the authors of the Voxseg Python package, including
[Nick Wilkinson](https://github.com/NickWilkinson37/) and
[Thomas Niesler](https://dsp.sun.ac.za/~trn/index.html).  Thanks, as well,
to [Han Sloetjes](https://www.mpi.nl/people/sloetjes-han)
for his help with issues related to ELAN's local recognizer specifications.

## Citing Voxseg-ELAN

If referring to this code in a publication, please consider using the following
citation:

> Cox, Christopher. 2022. Voxseg-ELAN: Voice activity detection for ELAN users. Version 0.1.1.

```@manual{cox22Voxsegelan,
    title = {Voxseg-ELAN: Voice activity detection for ELAN users},
    author = {Christopher Cox},
    year = {2022}
    note = {Version 0.1.1},
    }
```
