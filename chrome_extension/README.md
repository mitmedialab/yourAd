# YourAd

YourAd is an open-source browser extension and ad design tool that allows users to supplant their internet ads with custom replacements– designed by and for themselves. It uses Python/PIL to generate ads as specified by the user with a commandline tool, and works as a Chrome Extension.

For more details, see the write up here.

This is a fork of the Catblock Project; many thanks to those guys for their open-source work!

Included images are all non-attribution licensed images from pexel.com.

## To get it up and running:

1) pip install -r requirements.txt

2) put source images you'd like to use in your ads in 'source' folder

3) generate ads by calling 'python ad_creator.py'

4) load the extension in developer mode:
  * go to chrome://extensions in chrome
  * activate 'developer mode' in the top right of page with the checkbox
  * click 'load unpacked extension' and select 'yourad/chrome_extension' folder

off it goes!
