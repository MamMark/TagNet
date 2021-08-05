
----

## Index
- [Introduction](#introduction)
- [Installation](#installation)
- [Security](#security)
- [Operation](#operation)
- [Notebook Descriptions](#notebook-descriptions)
- [Notes](#notes)

----

## Introduction

Jupyter is an open source project that supports interactive computing.  One
of the core languages supported is Python.

The Tag project uses Jupyter notebooks to develop and test various
components of the TBS (basestation) software.  Notebooks exist for testing
the TagFS (fuse based Tag File System) and low level communications
drivers.

See [Notebook Descriptions](#notebook-descriptions) for details.


----

## Installation

- Login in to the RPi and run the following commands:
```
    sudo pip install jupyter ipywidgets
    sudo apt install -y python-seaborn python-pandas
    sudo apt install -y ttf-bitstream-vera
    sudo jupyter nbextension enable --py  widgetsnbextension

    # use --sys-prefix to install in an activated virtual environment
    jupyter nbextension enable --py --sys-prefix widgetsnbextension

    # additions so Jupyter can use Google maps
    sudo pip install pyproj
    sudo pip install gmaps
```

There is a pre-configured jupyter configuration file in the TagNet repository
```tag/TagNet/jupyter_noteboot_config.py```.  It may be out of date.

To use the pre-configured jupyter configuration do the following:
```
    # assumes that the TagNet repository has been installed in ~/tag
    cd ~        # cd to pi's home directory
    mkdir .jupyter
    cp tag/TagNet/jupyter_noteboot_config.py ~/.jupyter
```

Alternatively, you can regenerate a configuration file by excuting:
```
    jupyter notebook --generate-config
```

For security reasons you should edit the following fields:
```
    ## The IP address the notebook server will listen on.
    c.NotebookApp.ip = 'localhost'

    c.NotebookApp.port = 9000

    # set password to 'dogbreath'
    c.NotebookApp.password = u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
```

To generate your own password execute the following:
```
    # change 'dogbreath' to your desired password

    $ python
    > from IPython.lib import passwd
    > password = passwd("dogbreath")
    > password
    u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
    > CTL-D
```

----

## Security

Jupyter runs as a server on the RPi and enables the excution of arbritrary
code.  This is inherently a secutiry risk and needs to be protected.

We protect against intrusions in the following ways:

- The Jupyter server is hand started.  It will only run after you start it.
  See [Operation](#opration) below.

- The Jupyter server only allows connections on ```localhost:9000``` and can
  not be connected to except from the RPi itself.

- We use an explicit ssh tunnel from the work station to ```localhost:9000```
  on the RPi.

Only run Jupyter if you need it.

----

## Operation

Using Jupyter consists of two parts, starting the Jupyter kernel on
the RPi (device under test), and launching a web browser on the host
for interacting with the kernel.

For security reasons, all interaction with the RPi is done through
an encrypted ssh port forwarding tunnel.

- Start the ssh port forwarder

  From the workstation, launch the ssh tunnel.  ```dvt3``` is the RPi.
```
    ssh -N -f -L localhost:9000:localhost:9000 -o ServerAliveInterval=30 pi@dvt3 &> Tun.out

    -N  do not execute a remote command, just forward the port.
    -f  run in background after asking for any passwords.
    -L  local port forwarding (forwarding done on the dvt3 ssh server).  The
        first tuple, localhost:9000 tells the workstation ssh client to listen
        on port 9000 bound to localhost (127.0.0.1).  This port is then
        connected to the ssh server on dvt3 when is also connected to port
        9000 on dvt3's localhost.
```
> if you don't have ```authorized_keys``` set up you will be asked for a password.


- Start the Jupyter Kernel on the RPi

  Log into the RPi, and run:
```
    nohup jupyter notebook --no-browser --notebook-dir /home/pi/tag/TagNet
```

- Browse to the Jupyter Server from the Workstation

  Open a web browser on the workstation and enter the following address

```
    http://localhost:9000
```

> Because of the ssh tunnel from ```localhost:9000``` on the workstation to ```localhost:9000```
> on the RPi, the browser is talking to the Jupyter kernel running on the RPi.

----

## Notebook Descriptions

notebooks:
- Fuse_Tree_Dblk_IO.ipynb
- Fuse_Tree_Image_Load.ipynb
- Fuse_Tree_Test.ipynb
- Radio_Config_Info.ipynb
- Radio_Device_Image_Directory.ipynb
- Radio_Test_Bytes.ipynb
- Radio_Test_Modem.ipynb
- Radio_Test_Poll.ipynb
- Si446x_Device_GPS_Position.ipynb
- Si446x_Device_Load_Image.ipynb
- Si446x_Device_Load_Image.py
- Si446x_Device_Poll.ipynb
- Si446x_Device_Read_Dblk.ipynb
- Si446x_Device_Read_File.ipynb
- Sparse_File_Test.ipynb

notebooks/TagFuse_Tutorial:

- TagFuse_Dblk_IO.ipynb
- TagFuse_Find_Tags.ipynb
- TagFuse_network_test.ipynb
- TagFuse_Power_RSSI.ipynb
- TagFuse_radio_stats.ipynb
- TagFuse_Software_Load.ipynb
- TagFuse_tagdump.ipynb

----

## Notes

##### Run Jupter as Background Task

To start Jupyter on the RPi, use these commands
```
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py gmaps
#nohup jupyter notebook --no-browser --port=9000 &
su pi -c "nohup nice --adjustment=-20 jupyter notebook --browser=false --allow-root --port=9000 --notebook-dir /home/pi/Desktop/TagNet&"
```

#### Java

- What depends on Java?
- see if we can use default-jdk
```
  sudo apt install default-jdk
  sudo apt install openjdk-8-jdk
```

or

- use the JDK from Oracle.

  - visit http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html
  - click the download button of Java Platform (JDK) 8.
  - download jdk-8-linux-arm-vfp-hflt, ARM v6/7 Hard Float ABI.
  - Java SE Development Kit 8u172 (current is 8u301, we don't know if that works).
  - jdk-8u301-linux-arm32-vfp-hflt.tar.gz
  - jdk-8u301-linux-aarch64.tar.gz

- Log-in Raspberry Pi

  enter the command to extract jdk-8-linux-arm-vfp-hflt.tar.gz to /opt directory.
```
  sudo tar zxvf  jdk-8u172-linux-arm64-vfp-hflt.tar.gz -C /opt
```
- Set default java and javac to the new installed jdk8.
```
  sudo update-alternatives --install /usr/bin/javac javac /opt/jdk1.8.0_172/bin/javac 1
  sudo update-alternatives --install /usr/bin/java java /opt/jdk1.8.0_172/bin/java 1
  sudo update-alternatives --config javac
  sudo update-alternatives --config java
```
- After all, verify with the commands with -version option.

```
java -version
javac -version
```

-----------------------------------------------------------------------------------------------------

