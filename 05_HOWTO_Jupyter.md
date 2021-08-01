
### Using Jupyter

In browser window enter:

```
http://<device>.local:9000
```

Update Java first
```
* see if we can use default-jdx
```
  sudo apt install default-jdk
  sudo apt install openjdk-8-jdk
```

or

* use the JDK from Oracle.

  - visit http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html
  - click the download button of Java Platform (JDK) 8.
  - download jdk-8-linux-arm-vfp-hflt, ARM v6/7 Hard Float ABI.
  - Java SE Development Kit 8u172 (current is 8u301, we don't know if that works).
  - jdk-8u301-linux-arm32-vfp-hflt.tar.gz
  - jdk-8u301-linux-aarch64.tar.gz

* Log-in Raspberry Pi
enter the command to extract jdk-8-linux-arm-vfp-hflt.tar.gz to /opt directory.
```
  sudo tar zxvf  jdk-8u172-linux-arm64-vfp-hflt.tar.gz -C /opt
```
* Set default java and javac to the new installed jdk8.
```
  sudo update-alternatives --install /usr/bin/javac javac /opt/jdk1.8.0_172/bin/javac 1
  sudo update-alternatives --install /usr/bin/java java /opt/jdk1.8.0_172/bin/java 1
  sudo update-alternatives --config javac
  sudo update-alternatives --config java
```
* After all, verify with the commands with -version option.

```
java -version
javac -version
```

-----------------------------------------------------------------------------------------------------



## Install Jupyter

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

