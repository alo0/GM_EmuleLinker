GM_EmuleLinker
==============

Presentation
------------

**GM_EmuleLinker** is a [GreaseMonkey/Tampermonkey](https://tampermonkey.net/) script to add all [ED2K](https://en.wikipedia.org/wiki/EDonkey2000) links (with one click) into a remote [emule](https://www.emule-project.com)/[amule](https://www.amule.org/)/[mldonkey](https://github.com/ygrek/mldonkey) or any application installed on your system that handles ed2k links.</br>

It parsed the current HTML page and display all ed2k links found within the current page in a popup box displayed in the top left corner of the page.

![Main screen](https://github.com/alo0/GM_EmuleLinker/blob/master/screenshots/screenshot_main-0.9.png?raw=true)

Then you can add all of them in one click into your emule/amule/mldonkey application</br>

The script provide a settings screen to match your configuration and customize the popup box

![Settings screen](https://github.com/alo0/GM_EmuleLinker/blob/master/screenshots/screenshot_settings-0.9.png?raw=true)

How to install
--------------

1. Install the [Tampermonkey](https://tampermonkey.net/) plugin into your browser:</br>
    https://tampermonkey.net/
    </br>This script was originaly developped using [GreaseMonkey](https://www.greasespot.net/) but we recommend now to use Tampermonkey. 
    You could also use [Violentmonkey](https://violentmonkey.github.io/) but it is not officialy supported (not tested).

2. If your emule/amule/mldonkey application is on a remote server, you need to activate the webserver.</br>
    1. In emule, go to Settings -> Web Server -> \[x\] enable
        - set a port number (4711 is the default)
        - and a password
    2. if you use amule or mldonkey I am sure you know how to do it

3. Install this script in tampermonkey</br>
    Just copy and paste the content of this file [Emule Linker](https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.js)

    If you need help to install the script:
    https://tampermonkey.net/faq.php?ext=dhdg#Q102

4. Go to the settings screen</br>
    Just display an html page with ed2k links
    You can use the test sample page provided here: 
    [Test sample page](https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/test_sample.html)


    Click on Settings button on the top right, then fill in the fields accordingly. Passing the cursor over the labels will give you more explanations.

5. Set your configuration</br>
    Choose one of the "Ed2k Download Method" available
    - **Your system default** will use the application installed on your machine. The one that handle by default ed2k links
    - **(remote) amule/emule/mldonkey** if your application is on a remote machine
    - **custom (experimental)** will send the e2dk links to your own webserver, so that you process it as you see fit.

    Then fill in the following fields
    - **Url** in the form of `http://ip:port/`
    - **Password** if you entered any (only available for emule/amule)
    - **Category** if you need to be able to choose a category you should described it in the form of `*label1=0;label2=1;...`
        - emule: `default=0;*Audio=1` the number is the tab number in emule. The label prefixed by a `*` will be the default choice (`Audio` in this case).
        - amule: `*Audio=audio;Video=Video`. amule don't use numbered tab but the name of the tab within the application. The label prefixed by a `*` will be the default choice
        - mldonkey: does not support categories

    Don't forget to Save before closing the dialog screen.

6. You should now be able to add all links of a page to your emule/amule/mldonkey system

7. (optional) restrict the pages where this script is active by modifying the @include variable of this script. By default it is active on all pages you visit.</br>
https://www.tampermonkey.net/faq.php#Q103


Support
-------

The following browsers are supported:
- Firefox
- Chrome

Tests are done on the latest stable version of these browsers with tampermonkey, emule (local and remote) and amule (remote only) applications.


Limitations
-----------

Modern browsers don't like javascript that silently open windows or plays with (un)focus of your browser. Even if it is initiated by one of your action. In modern world it is considered as bad behavior and a security risk. I tried several methods to enhance the way this script send the links to emule/amule/mldonkey but only the old way implemented here does not require complex user interactions or browser/server specific settings.

I use a GET call in a new window. All arguments are passed in URL, including the password. Therefore I strongly recommend to access your emule/amule/mldonkey using https to hide these information. Thus all parameters will be hidden from people on the same network. Please note that the whole URLs (including links and passwords) are visible in your browser history.

All of these comments does not apply if you use the local method (Ed2k Download Method=Your system default)