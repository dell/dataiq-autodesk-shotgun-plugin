The shotgun plugin connects to the shotgun API and applies tag to the shots found on the filesystem

# Prerequisite

Have DataIQ running on the host machine.

Must have Python pip installed. May require the epel-release package for Red Hat.

## Installation

### Create directories to host plugin

```bash
(shotgun) $ mkdir "build"
(shotgun) $ mkdir "dist"
```

### Migrate Host Storage

```bash
(shotgun) $ cp -rv "hoststorage/." "build"
```

### Pull Dependencies

```bash
(shotgun) $ cd "build"
(build) $ python2 -m pip download -d deps2 -r requirements.txt

```

### Build Host Storage

We are packaging the hoststorage and Python dependencies into a single archive file so that this plugin can be installed on any DataIQ host. It is self-contained so that running the plugin does not require a connection to the outside internet to download dependencies at runtime.

```bash
(build) $ tar -czvf "../dist/shotgun-plugin-1.0.0.tar.gz" *
```

### Initialize Plug-in Manager

```bash
(shotgun) $ /opt/dataiq/plugin_manager/bin/plugin_manager init
```

### Install the plug-in using the host storage archive

```bash
(shotgun) $ /opt/dataiq/plugin_manager/bin/plugin_manager install shotgun-plugin plugin-centos-base
-f "dist/shotgun-plugin-1.0.0.tar.gz"
```

### Start the installed plug-in

```bash
~ $ /opt/dataiq/plugin_manager/bin/plugin_manager start shotgun-plugin
```

## Plugin configuration

### Configure autotagging

Shotgun plugin needs tags to identify shotgun shots. This is done using the autotagging feature.

The shotgun plugin assumes the following directory structure on filesystem.

```
/volumename/showname/sequences/sequencename/shots/shotnumber/

```
Where volumename, showname, sequencename, and shotnumber are variable.

A /sequences directory (case sensitive) must exist at the third level depth and a /shots directory must exist at the fifth level depth. 


Notes: 
-	This directory pattern is hard-coded into the example shotgun plugin.   
-	If your actual production directory structure varies from the above example, both the DataIQ regular expression autotag rule and the actual python API to Shotgun will need to be modified to match actual directory structure in production.
-	shownames can actual span multiple filesystem volumes (example: production storage and archive storage) if first level autotag regular expression matches on multiple volumes
-	The python API call to Shotgun can then also be refined for further efficiencies


In DataIQ go to **settings** > **data management configuration** > **Other settings** > **Autotagging configuration file**

<p align="center">
<img src="./assets/dataiq-settings.png" />
<img src="./assets/autotagging.png" />
</p>

Add at the end of file the following:
Replace the <VOLUME NAME> with your volume name

```
match /<VOLUME NAME>/([^/]+)/sequences/([^/]+)/shots/([^/]+)
   max_depth 6
   apply_tag shot/$1_$2_$3
```

<p align="center">
<img src="./assets/autotagging-configuration.png" />
</p>

### Configure Shotgun plugin

In DataIQ go to **settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Edit configuration**

<p align="center">
<img src="./assets/plugin-list.png" />
</p>

and edit the global configuration:

```yml
"Global Configurations":
  shotgunAPIUrl: "YourShotgunAPIUrl"
  shotgunAPIScriptName: "YourShotgunAPIScriptName"
  shotgunAPIKey: "YourShotgunAPIKey"
  expirationDelay: 7
```

<p align="center">
<img src="./assets/global-configuration.png" />
</p>

### Enable Shotgun plugin

Once configured you can enable the plugin by going to:
**settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Enable**

<p align="center">
<img src="./assets/enable-plugin.png" />
</p>

The plugin is automatically executed everyday at 1:00 AM (You can also edit the Cron jobs in the configuration file)

**settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Edit configuration**

<p align="center">
<img src="./assets/cronjob.png" />
</p>

### Trigger Shotgun plugin manually

You can trigger the plugin manually by selecting a folder on DataIQ dashboard

<p align="center">
<img src="./assets/trigger-manually.png" />
</p>

Select the "Actions" tab and click **Run shotgun plugin**

<p align="center">
<img width="250" src="./assets/run-plugin.png" />
</p>

## Configure Shotgun

### Register on Shotgun

Create an account on https://www.shotgunsoftware.com/ and signin

You have access to a free 30 days trial

### Create a new project

<p align="center">
<img src="./assets/new-project.png" />
</p>

### Create a new sequence

<p align="center">
<img src="./assets/new-sequence.png" />
</p>

<p align="center">
<img src="./assets/new-sequence-1.png" />
</p>

### Add a a new shot

<p align="center">
<img src="./assets/shot.png" />
</p>

<p align="center">
<img src="./assets/new-shot.png" />
</p>

### Attach the shot to the create sequence

<p align="center">
<img src="./assets/add-to-sequence.png" />
</p>

<p align="center">
<img src="./assets/add-to-sequence-validate.png" />
</p>

### Create a new API

Go to Scripts

<p align="center">
<img width="200" src="./assets/scripts.png" />
</p>

<p align="center">
<img src="./assets/new-script.png" />
</p>

Once created [edit the global configuration with the API credentials](#configure-shotgun-plugin)

### Create the folder hierarchy

On the host machine go to your mounted volume and create the following folders:

```bash
$ mkdir -p dataiqtest/sequences/sequence/shots/shot
```

If you look carefully, our hierarchy is composed of the following:

```
<PROJECT_NAME>/SEQUENCES/<SEQUENCE_FOLDERS>/SHOTS/<SHOT_FOLDERS>

.
`-- sequences
    `-- sequence
        `-- shots
            `-- shot
```

- The sequences folder is composed of folders within the same name of the sequences created on Shotgun
- The shots folder is composed of folders within the same name of the shots created on Shotgun

For instance if we have a shot named 'test' we will have the following tree:

```
.
`-- sequences
    `-- sequence
        `-- shots
            `-- shot
            `-- test
```

### Run Shotgun plugin

Now you can re-scan volumes and [trigger Shotgun manually](#trigger-shotgun-plugin-manually)

If everything worked correctly you will have your shots tagged!

<p align="center">
<img src="./assets/tagged.png" />
</p>

### Uninstall the plug-in

Disable the plug-in in DataIQ, go to **settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Edit configuration**

<p align="center">
<img src="./assets/disable.png" />
</p>

Stop the plug-in

```bash
~ $ /opt/dataiq/plugin_manager/bin/plugin_manager stop shotgun-plugin
```

Delete plug-in componenets

```bash
~ $ /opt/dataiq/plugin_manager/bin/plugin_manager rm shotgun-plugin
~ $ rm -rf /opt/dataiq/maunakea/data/plugins/shotgun-plugin/
```

