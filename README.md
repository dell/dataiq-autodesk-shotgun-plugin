# Prerequisite

Have DataIQ running on the host machine

## Installation

### Create a temporary folder for building process

```bash
$ mkdir build_tmp
```

### Copy plugin-template-0.1 folder content into previously created temporary folder

```bash
$ cp -r ./plugin-template-0.1/* ./build_tmp/
```

### Copy plugin code in the template sample

```bash
$ cp -r ./cn_shotgun/*.py ./build_tmp/plugin-shotgun/plugin
```

### Copy plugin configuration

```bash
$ cp -r ./build_tmp/plugin-shotgun/plugin/ca.control ./build_tmp/dataiq-shotgun
```

### Change directory

```bash
$ cd ./build_tmp/plugin-shotgun
```

### Rebuild docker image

```bash
$ ./rebuild
```

### Start container in debug mode

```bash
$ ./debug
```

### Get pods name and copy the pod name related to plugin-shotgun

```bash
$ ./listpods
```

e.g:
**plugin-shotgun-5f7fff54c5-s22mt**

```
claritynow-6b8b9568f7-9g47x       1/1     Running     0          60m
claritynow-plugin-init-clhrp      0/1     Completed   0          60m
clew-55cd5dd466-bskss             1/1     Running     0          61m
imanager-667cd998c-kh5l9          1/1     Running     0          60m
ixui-5db7946d5f-2nvkt             1/1     Running     0          61m
keycloak-0                        1/1     Running     0          58m
keycloakdb-0                      1/1     Running     0          61m
plugin-shotgun-5f7fff54c5-s22mt   1/1     Running     0          67s
```

### Connect to container

```bash
$ kubectl exec -it -ndataiq <POD NAME> bash
```

Replace <POD NAME> with the correct value.
e.g:

```
kubectl exec -it -ndataiq plugin-shotgun-5f7fff54c5-s22mt bash
```

### Start plugin server

```bash
$ flask run --host=0.0.0.0 --port=5000
```

## Plugin configuration

### Configure autotagging

Shotgun plugin needs tags to identify shotgun shots. This is done using the autotagging feature.

In DataIQ go to **settings** > **data management configuration** > **Other settings** > **Autotagging configuration file**

<div style="text-align:center">
<img src="./assets/dataiq-settings.png" />
<img src="./assets/autotagging.png" />
</div>

Add at the end of file the following:
Replace the <VOLUME NAME> with your volume name

```
match /<VOLUME NAME>/([^/]+)/sequences/([^/]+)/shots/([^/]+)
   max_depth 6
   apply_tag shot/$1_$2_$3
```

<div style="text-align:center">
<img src="./assets/autotagging-configuration.png" />
</div>

TODO: Explain how Shotgun works

### Configure Shotgun plugin

In DataIQ go to **settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Edit configuration**

<div style="text-align:center">
<img src="./assets/plugin-list.png" />
</div>

and edit the global configuration:

```yml
"Global Configurations":
  shotgunAPIUrl: "YourShotgunAPIUrl"
  shotgunAPIScriptName: "YourShotgunAPIScriptName"
  shotgunAPIKey: "YourShotgunAPIKey"
  expirationDelay: 7
```

<div style="text-align:center">
<img src="./assets/global-configuration.png" />
</div>

### Enable Shotgun plugin

Once configured you can enable the plugin by going to:
**settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Enable**

<div style="text-align:center">
<img src="./assets/enable-plugin.png" />
</div>

The plugin is automatically executed everyday at 1:00 AM (You can also edit the Cron jobs in the configuration file)

**settings** > **data management configuration** > **plugins** > **Select Shotgun plugin** > **Edit configuration**

<div style="text-align:center">
<img src="./assets/cronjob.png" />
</div>

### Trigger Shotgun plugin manually

You can trigger the plugin manually by selecting a folder on DataIQ dashboard

<div style="text-align:center">
<img src="./assets/trigger-manually.png" />
</div>

Select the "Actions" tab and click **Run shotgun plugin**

<div style="text-align:center">
<img src="./assets/run-plugin.png" />
</div>
