# Introduction

A TagNet base station (TBS) is hosted on a Raspberry Pi running the ComitUp
variant of the Raspberry Pi OS (RPiOS).  This is a Debian based Linux
Operating System that provides for headless connection to WiFi networks.

The TBS acts as a gateway between a cluster of Tags and the outside world
via an external IP based network connection.  This connection can be either
a hardwired ethernet or typically a wireless connection.

When a base station first boots up or can not find a previously connected
network, the WiFi interface will be brought up as a hotspot.  A host
computer can then connect to this hotspot and access the base station
directly.  Alternatively, the base station can be configured to connect to
an existing wireless network and accessed via that network.

Either way, the host can then access the base station and its cluster of
Tags via this network connection.

We use a version of RPiOS including ComitUp.  This version of RPiOS
supports all versions of the Raspberry Pi (RPi) except the RPi-Pico.  This
includes the Pi 0W, 1, 2, 3, 3+, and Pi 4.

For TBS use, a Pi 3 or 4 is required.

> Assumed that you have a rudimentary understanding of Linux systems and
> emacs (only needed for **Magit** install/use.
>
> Later in this document, there will be references to a machines named ```zot``` and
> ```dvt4```.   ```Zot``` is the name of an example host, being used to connect to
> the example RPi TBS being built, ```dvt4```.
>


## ComitUp Overview

ComitUp can be found at:

    Overview:       https://davesteele.github.io/comitup/
    Desktop:        https://steele.debian.net/comitup/image_2021-06-30-Comitup.zip
    Lite:           https://steele.debian.net/comitup/image_2021-06-30-Comitup-lite.zip

Typically, the Lite image is used for a TBS, which does not include any desktop software.

The 2021-06-30 image is based on the 2021-05-07 Debian 10 (Buster) image using the Linux
5.10.17 kernal with gcc 8.3.   See https://en.wikipedia.org/wiki/Raspberry_Pi_OS for more
details.

Once a base system has been installed and configured, additional TagNet software needs to be
installed.   A future combined image may be constructed that will include all this additional
software.


## Installation Requirements

Installation requires the following:

  * Host: computer that can write a SD card (Mac OS, Linux, or Windows)
  * SD slot: either direct or USB SD adapter.
  * SD: 32GB or larger SD class 10 card
  * Internet: WiFi or hardwired ethernet.
  * BalenaEtcher: software for writing image.   https://www.balena.io/etcher/


Note, make sure to use https://www.balena.io/etcher/, and not www.etcher.net which provides a bogus
version of Etcher which doesn't work correctly.


----------------------------------------------------------------------------------------------------

## Installation

### Download

Download onto the host machine.

choose [RPiOS_Comitup_Full](https://steele.debian.net/comitup/image_2021-06-30-Comitup.zip) or
[RPiOS_Comitup_Lite](https://steele.debian.net/comitup/image_2021-06-30-Comitup-lite.zip).

        cd ~/Downloads
        wget https://steele.debian.net/comitup/image_2021-06-30-Comitup-lite.zip

### Flash
flash the image using Etcher

  * download BalenaEtcher from https://www.balena.io/etcher/.
  * insert a 32 GB or larger SD into the SD slot
  * select the file downloaded above.
  * select the flash drive where you inserted the SD.

    > _it is very important that you select the correct drive._
    >
    > _**ANY** previous contents  will be erased._

  * click Flash.

### Initial Boot on the RPi.
  * Insert the SD into the RPi SD slot.
  * apply power.
  * Wait for a solid red light and the green light stops flashing.

    > During the initial boot, the filesystem on the SD will be expanded to
    > fill the available space.
    >
    > This can take some time.


### Connect the RPi to your local network

The new RPi needs to be connected to your local network to perform additional
configuration.  This can be accomplished by connecting to a physical Ethernet or
a WiFi network.

For WiFi networks, if **comitup** can not connect to a local wifi access point, it
will establish a custom hotspot and run a **comitup-web** service.
This allows connection and initial configuration via WiFi.

From a WiFi enabled computer, look for a WiFi network name of the form
```comitup-<nnn>```, where &lt;nnn&gt; is a persistent number.

If supported a captive portal will pop-up for wifi network configuration or
one can browse to _comitup-&lt;nnn&gt;.local_, or `http://10.41.0.1/`.

Once the popup or browser is up, you will be able to configure the WiFi
network name and its password.  Click _Connect_.


### Initial Login

The RPi initial hostname is ```comitup-<nnn>``` where ```nnn``` is the
same number as above.  You can connect via ssh using the user name ```pi``` with
the password ```raspberry```.

> _the default password is ```raspberry``` and is well known.  This is a
> huge security hole and one of the first things you should change._

```
    xyz (1)$ ssh pi@comitup-596
    pi@comitup-596's password: raspberry

    Linux comitup-596 5.10.17-v7l+ #1421 SMP Thu May 27 14:00:13 BST 2021 armv7l

    The programs included with the Debian GNU/Linux system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/*/copyright.

    Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
    permitted by applicable law.
    Last login: Thu Jul 22 04:57:57 2021 from 192.168.1.99

    SSH is enabled and the default password for the 'pi' user has not been changed.
    This is a security risk - please login as the 'pi' user and type 'passwd' to set a new password.

    pi@comitup-596:~ $ sudo -s
    root@comitup-596:/home/pi# passwd pi
    New password:
    Retype new password:
    passwd: password updated successfully
    root@comitup-596:/home/pi# exit
    pi@comitup-596:~ $
```

#### Modifying Basic Configuration

The initial configuration needs to be modified.  Headless instances need to be modified via the
command line.  RPiOS provides a text based GUI to make these modifications.

```
    pi@comitup-596:~ $ sudo raspi-config

    1. System Options
       [S4] Hostname
            change hostname
       [S5] Boot/Auto Login
            [B1] Text Console - no autologin
       [S7] Disable splash screen
    2. Display Option
    3. Interface Options
       [P4] enable SPI kernel module
    4. Performance Options
    5. Localization Options
       [L1] Locale
            deselect en_GB.UTF-8 UTF-8
            select   en_US.UTF-8 UTF-8
            default  en_US.UTF-8 UTF-8
       [L2] Timezone
            America/Los Angeles
       [L3] Keyboard
       [L4] WLAN Country
            US
    6. Advanced Options

    Finish, the system will reboot.
```

- After the system reboots, it will come up with its new hostname, ie. ```dvt4```.

- In the remainder of this document ```zot``` is the host and ```dvt4``` is the RPi being
configured.


#### Update and Upgrade System Software

```
    sudo apt update
    sudo apt full-upgrade -V
```

> ```apt full-upgrade``` may remove packages if needed to upgrade the system.  If this
> is an issue, use ```apt upgrade``` instead.


-------------------------------------------------------------------------------------------------

#### Install Additional Core Software
``` bash
    sudo apt install               \
        git gitk ntp dnsutils      \
        python-twisted sshfs       \
        libusb-dev libreadline-dev \
        emacs emacs-el

    sudo apt install               \
        python-dev python-rpi.gpio

    sudo apt install               \
         fuse libfuse2 libfuse-dev \
         python2.7-llfuse python3-llfuse
```

> Installation of various packages can involve downloading git repositories and
> other files.   All of these downloads go into a top level directory called ```~/tag```.
> This keeps all basestation software used for installation and later development
> in one directory structure.

#### Install local dot files
- Install standard dot files into home directory of ```pi```.
``` bash
    mkdir ~/tag
    cd    ~/tag
    git clone -o mm https://github.com/MamMark/dot-files.git
    SRC_DIR=./dot-files/
    DST_DIR=~/
    FILES=".bash_aliases .bash_functions .bash_login .bash_logout .bashrc .emacs.d \
        .environment_bash .gdbinit .gitconfig .gitignore .mspdebug"
    echo -e "\n*** dots from $SRC_DIR -> $DST_DIR ***"
    (for i in $FILES; do echo $i; done) | rsync -aiuWr --files-from=- $SRC_DIR $DST_DIR
```

- set up initial .ssh directory.
``` bash
    cd ~
    mkdir .ssh
    chmod go-rwx .ssh
```

- edit .bashrc to change EXPECTED_USER to 'pi' (was 'xyz').

- log out.  When you log back in you will be using the new dot files.

#### Install SSH authorized users
- To enable passwordless connection via ```SSH```, one can install one's ssh key into
  the ```.ssh/authorized_keys``` files.
- This is done from a host with your authorized_keys already set up.
```
    zot (5): scp .ssh/authorized_keys pi@dvt4:.ssh/
    pi@dvt4's password:
    authorized_keys                                                  100%  734   348.2KB/s   00:00
    zot (6):
```

----------------

### Log back into the RPi being built.
```
    ssh -AX dvt4
```

#### Install Magit

> **Magit** is a full interface to the version control system, Git.
> It runs inside of emacs.
>
> Optional but highly recommended.

Using a terminal window, execute ```emacs -nw```.

On startup, emacs will execute ~/.emacs.d/init.el which contains
the following:
``` lisp
    (require 'package)
    (add-to-list 'package-archives '("melpa" . "http://melpa.org/packages/") t)
    (package-initialize)
    (when (not package-archive-contents)
      (package-refresh-contents))
```

you will see emacs fetch various components from melpa.  After initialization
has completed, execute:

    M-x package-install RET magit RET


## Install Required Python Packages
These packages are required by TagNet BaseStation applications.
```
    cd ~/tag
    git clone https://github.com/MamMark/py-spidev.git
    cd py-spidev/
    sudo python setup.py install
    sudo usermod -a -G spi pi
    groups

    sudo pip install future machinist fusepy chest
    sudo pip install construct==2.5.2
    sudo pip install twisted==13.1.0
    sudo pip install txdbus==1.1.0
    # sudo pip install RPi.GPIO      # already installed by comitup
```

#### Download source trees for TagNet and Tag tools
```
    cd ~/tag
    git clone -o mm https://github.com/MamMark/mm.git
    git clone -o mm https://github.com/MamMark/TagNet.git
```

Work in progress can be found at the following repositories/branches:

```
    cd ~/tag/mm
    git remote add -f cire https://github.com/cire831/mm.git
    git checkout -t cire/cire_working

    cd ~/tag/TagNet
    git remote add -f cire https://github.com/cire831/TagNet.git
    git checkout -t cire/cire_working
```

## Install TagNet and Tag Tools
``` bash
    cd ~/tag/TagNet
    for d in si446x tagnet tagfuse; do
        echo '***' $d '***'
        (cd $d; sudo python setup.py install);
    done
```

``` bash
    cd ~/tag/mm/tools/utils
    for d in tagcore tagdump tagvers binfin pix tagctl ubxdump ; do
        echo '***' $d '***'
        (cd $d; sudo python setup.py install);
    done
```


## Install Jupyter (Optional)

#### used by jupyter for google maps
```
    sudo pip install pyproj
    sudo pip install gmaps
```

##### Install Jupyter Software
This application is used for development and testing purposes. Currently there are notebooks for low level radio device testing and TagFuse related testing.
```
cd ~/
sudo pip install jupyter
sudo apt install -y python-seaborn python-pandas
sudo apt install -y ttf-bitstream-vera
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
```
##### Generate Jupter Password

```
$ python
> from IPython.lib import passwd
> password = passwd("dogbreath")
> password
u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
> CTL-D
'sha1:1991fa41bea2:3c719e82a4e784e2affb6fb3b25b81d17e317bc0'

'sha1:27fa5b4a2d6c:b09e16f0242823eda500e7474a6a46f6f12ffc38'
```

##### Build Jupyter Configuration
Build the default Jupyter configuration settings (should be in your home directory at ```/home/pi/.jupyter/jupyter_notebook_config.py```)

```
jupyter notebook --generate-config
```

Edit these three lines in jupyter_notebook_config.py (produced in previous step)
```
c.NotebookApp.password = u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
c.NotebookApp.ip = '*'
c.NotebookApp.port = 9000
```

##### Run Jupter as Background Task
To start Jupyter on the RPi, use these commands
```
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py gmaps
#nohup jupyter notebook --no-browser --port=9000 &
su pi -c "nohup nice --adjustment=-20 jupyter notebook --browser=false --allow-root --port=9000 --notebook-dir /home/pi/Desktop/TagNet&"
```

--------

### Shared Development Folders (Optional)

>
> upstairs is the host, ie. ```zot```.   Basestation (RPi) is ```dvt4```
>

#### Mount basestation on host.  (```dvt4``` -> ```zot```)

> See 03_HOWTO for mounting host <-> basestation.  
> Mac OS or Linux.


#### Basestation sharing network shared folder.

Mount a Network Shared Folder/Workstation.

##### First Time
Add usergroup required to share files
```
sudo groupadd -g 504 devgrp
sudo usermod -a -G devgrp pi
```
Need to set the umask to allow sharing with Mac user. This is done by editting the ```.bash_login``` script to change.
```
umask 2
```

##### Permanent Mount
```
sudo mkdir /mnt/neptune
sudo mkdir /mnt/tag_integration
```
Add the following line to /etc/mount
```
//neptune.local/tag_integration /mnt/neptune cifs exec,noperm,_netdev,nosetuids,sec=ntlmssp,file_mode=0777,dir_mode=0777,user=pi,pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw  0 0
```

##### One-time Mount
```
sudo mount -t cifs //neptune.local/tag_integration /mnt/neptune -o exec,noperm,_netdev,nosetuids,sec=ntlmssp,file_mode=0777,dir_mode=0777,user=pi,pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw
```

##### Mount network shared file system on mac

create a group named devgrp with number 504.
```
dscl . list /Groups PrimaryGroupID
```

ON MAC, see [apple/HT204445](https://support.apple.com/en-us/HT204445) for more details.
* add user ```pi``` and group ```devgrp```
* use finder to connect to server
* use finder to Go/Connect_to_Server with ```smb://solar.local```
* specify ‘Open’ as folder to be mounted
* find the newly mounted folder at ```/Volumes/Open```

------------------
------------------

### Notes, Issues, and Ideas

#### Some steps to automating Rasbian Configuration

1. enable SPI
    1. Run this command: sudo nano /boot/config.txt
    2. Add this at the end of the file: dtparam=spi=on
    3. Save file pressing: CTRL+X, Y and Enter
    4. Reboot your system: sudo reboot
2. set hostname
```
* hostnamectl set-hostname
or
* sudo nano /etc/hostname
* sudo /etc/init.d/hostname.sh
* sudo reboot
```
3. country
4. timezone
    * timedatectl set-timezone America/Los_Angeles
5. set locale
    * one way
        * sudo nano /etc/default/locale
        * sudo locale-gen --purge it_IT.UTF-8 en_US.UTF-8 && echo "Success"
        * sudo locale-gen en_US.UTF-8
        * sudo dpkg-reconfigure locales
    * another
```
$ sudo locale-gen en_US.UTF-8 # Or whatever language you want to use
$ sudo dpkg-reconfigure locales
$ sudo nano /etc/default/locale
LANG="en_US.UTF-8"
LANGUAGE=“en_US”
```

#### wpa_supplicant.conf

> By default, we use ComitUp and this section should not be used.

For WiFi access, add access point information to /boot/wpa_supplicant. (comitup does
handles this differently, so don't mix the two).
```
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
    ssid="teahouse"
    psk=""
    key_mgmt=WPA-PSK
}
```

----

### Using Jupyter

In browser window enter:

```
http://<device>.local:9000
```

Update Java first
```
* Visit http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html, click the download button of Java Platform (JDK) 8. Click to Accept License Agreement, download jdk-8-linux-arm-vfp-hflt.tar.gz for Linux ARM v6/v7 Hard Float ABI.  Java SE Development Kit 8u172, Linux ARM 64 Hard Float ABI
    * Log-in Raspberry Pi, enter the command to extract jdk-8-linux-arm-vfp-hflt.tar.gz to /opt directory.
sudo tar zxvf  jdk-8u172-linux-arm64-vfp-hflt.tar.gz -C /opt
    * Set default java and javac to the new installed jdk8.
sudo update-alternatives --install /usr/bin/javac javac /opt/jdk1.8.0_172/bin/javac 1
sudo update-alternatives --install /usr/bin/java java /opt/jdk1.8.0_172/bin/java 1
sudo update-alternatives --config javac
sudo update-alternatives --config java
    * After all, verify with the commands with -version option.
java -version
javac -version
```

```


```



-----------------------------------------------------------------------------------------------------
-----------------------------------------------------------------------------------------------------

### Verify 32 bit execution environment

The Raspberry Pi 3 and 4 are both based on 64 bit ARM cores.  However, due to various reasons RPiOS
currently only supports 32 bit.  This can be verified via the following:

```
    dvt4 (1): getconf LONG_BIT
    32
    dvt4 (2): uname -a
    Linux dvt4 5.10.17-v7l+ #1421 SMP Thu May 27 14:00:13 BST 2021 armv7l GNU/Linux
    dvt4 (3):
```

The ```32``` returned above indicates 32 bit.  ```armv7l``` in the result of ```uname``` also indicates
the same thing.
