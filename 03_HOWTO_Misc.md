
----

## Index

- [Connect a Base Station to Wifi](#connect-a-base-station-to-wifi-network)
- [Grip: render markdown](#grip-render-markdown-files)
- [Remote mounting file systems](#remote-mounting-file-systems)
- [Ether/Ether direct connect](#etherether-direct-connect)
- [AutoConf Ubuntu Ethernet](#autoconf-ubuntu-ethernet)
- [Network Attached Storage](#using-network-attached-storage-filesystems)
- [Notes, Issues, and Ideas](#notes-issues-and-ideas)

----

### Connect a Base Station to Wifi network.

If this base station has already been connected to this wifi network, it will
automatically reconnect.

If not previously connected to this network follow these steps:

- plug the base station in and power it up.
- look for the local wifi network ```comitup-<nnn>```
- connect to this network.
- 3 different methods to connect:
  - Look for a pop up captive portal (to configure the connection)
  - browse to ```http://comitup-<nnn>.local```
  - browse to ```http://10.41.0.1```
- select an available wifi net and click ```connect```

```<nnn>``` above is a persistent number assigned automatically to this RPi.


----

### Grip: render markdown files

```
  pip  install grip   (python systems)
  brew install grip   (Mac OS X)
```

  from github:
```
    git clone https://github.com/MamMark/grip.git
    cd grip
    sudo python setup.py install
```

  Using grip:

```
    grip <markdownfile>
    grip --pass=<token> <markdownfile>
    * Running on http://localhost:6419/ (Press CTRL+C to quit)
```
point a browser at http://localhost:6419/ to see your rendered doc.

-  you may run into the API rate limit in which case you should
   use a github personal access token.  You need a github login.

   see https://github.com/MamMark/grip#access

- Visit ```Settings->Developer settings->Personal access tokens``` on github.

  https://github.com/settings/tokens/new?scopes=


----

###  Remote mounting file systems.

```sshfs``` is used to perform the mount via a ssh tunnel.

- One should set up ssh keys and an authorized user prior to mounting.
  This will greatly simplify operation.

```rmt``` is the remote host whose file system we want to mount, rmt user: ```xyz```


#### Linux -> Linux:
```
    sudo apt install sshfs
    sudo mkdir /mnt/rmt/<dir>
    sudo sshfs -o allow_other xyz@rmt:<remote_dir> /mnt/rmt/<dir>
```

#### Linux -> MacOS:

##### Mac OS installation:

Download and install:
- https://github.com/osxfuse/osxfuse/releases/download/macfuse-4.1.2/macfuse-4.1.2.dmg
- https://github.com/osxfuse/sshfs/releases/download/osxfuse-sshfs-2.5.0/sshfs-2.5.0.pkg

Due to permission problems, the easist way to do a remote mount is onto
a filesystem that you have write permission for.

Mounting remote filesystem with sshfs

```
    chdir ~
    mkdir -p rmt/<dir>
    sshfs xyz@rmt:<remote_dir> rmt/<dir>
```

for example, remote machine ```zot```, directory ```tag```, mounted to ```~/zot/tag``` on local machine.

```
    chdir ~
    mkdir -p zot/tag
    sshfs zot.lan:tag zot/tag
```

Note: ```sshfs``` on Mac OS is implemented as a ```FUSE```, file system in
user space.  All transfers from the remote filesystem across an encrypted
SSH tunnel.  As such it can be quite slow.

Additionally, the mount on Mac OS X can become stuck or unresponsive.  You can force
an unmount using one of the following:

```
    umount rmt/<dir>
    diskutil umount force rmt/<dir>
```

References:
- https://osxfuse.github.io
- https://github.com/osxfuse/osxfuse/wiki/SSHFS

----

### Ether/Ether direct connect

(see the [AutoConf Ubuntu Ethernet](#autoconf-ubuntu-ethernet) section below for self-assign configuration)

- plug in an ethernet cable between the pi and the computer  
  both the pi and the computer will use self-assigned IP numbers.

- ping using ```<pi-name>.local```

- login using ```ssh pi@<pi-name>.local```


----

### AutoConf Ubuntu Ethernet

Configure an Ubuntu/Debian based linux system to use ```<name>.local``` identifiers.
Uses Avahi, zeroconf auto discover.

Requires the following:
```
    # need the following
    # avahi-daemon avahi-discover avahi-utils libnss-mdns mdns-scan
    sudo apt install avahi-daemon avahi-discover avahi-utils libnss-mdns mdns-scan

    # tell netmanager not to bother
    sudo nmcli nm enable false

    # configure the ethernet on the Linux host to self-assign
    sudo avahi-autoipd eth0 -D

    # once done turn NetworkManager back on
   sudo nmcli nm enable true
```

----

### Using Network Attached Storage filesystems

Various kinds of NAS storage, for this example we assume the protocol used
is ```CIFS``` (aka ```Samba```).  This protocol requires the installation of the
```cifs-utils``` package (usually installed by default).

#### Setup
Add usergroup required to share files, set umask.
```
  sudo groupadd -g 504 devgrp
  sudo usermod -a -G devgrp pi
  sudo mkdir /mnt/neptune
  umask 2
```

#### Permanent Mount
```neptune``` is a NAS hosting the drive ```tag_integration```.

Add the following line to /etc/fstab
```
//neptune.local/tag_integration /mnt/neptune cifs exec,noperm,_netdev, \
        nosetuids,sec=ntlmssp,file_mode=0777, dir_mode=0777, user=pi,  \
        pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw  0 0
```

to mount the disk, execute ```mount /mnt/neptune```.

##### One-time Mount
```
  sudo mount -t cifs //neptune.local/tag_integration /mnt/neptune    \
        -o exec,noperm,_netdev,nosetuids,sec=ntlmssp,file_mode=0777, \
           dir_mode=0777,user=pi,pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw
```

##### Mount network shared file system on MacOS

create a group named devgrp with number 504.
```
dscl . list /Groups PrimaryGroupID
```

MacOS X: see [apple/HT204445](https://support.apple.com/en-us/HT204445) for more details.
* add user ```pi``` and group ```devgrp```
* use finder to connect to server
* use finder to Go/Connect_to_Server with ```smb://solar.local```
* specify ‘Open’ as folder to be mounted
* find the newly mounted folder at ```/Volumes/Open```

----

### Notes, Issues, and Ideas

#### Programatic modification of some configuration.

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

----

#### Verify 32 bit execution environment

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
