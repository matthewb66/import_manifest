# Synopsys Import Manifest Script - import_manifest.py
# OVERVIEW
This script is provided under an OSS license as an example of how to use the Black Duck APIs to import components from a manifest list.

It does not represent any extension of licensed functionality of Synopsys software itself and is provided as-is, without warranty or liability.

# DESCRIPTION

The `import_manifest.py` script imports components (as manually added components) from a component list to a Black Duck project/version by searching for component name and component version matches in the Black Duck KnowledgeBase.

It has 2 modes of operation which are required to be executed in sequence for each import activity.

The first mode (`kblookup`) reads the input component list file to create an output file of KB lookup matches for the components, also reporting a list of non-matches. Note that the script stops at 500 input components in order to avoid a timeout of the API connection session (20 minutes). The script can be re-run on the same component list if more than 500 components need to be processed.

The output KB lookup file created by kblookup mode can then be reviewed and supplemented manually to replace or add components to ensure correct matches during the import phase.

The second mode (`import`) reads the input component list and the KB match file to add manual components to the specified Black Duck project/version.

The following diagram explains the flow of data for the 2 modes:

![](https://github.com/matthewb66/import_manifest/blob/master/images/im_process_map.png)

# PREREQUISITES

Python 3 and the Black Duck https://github.com/blackducksoftware/hub-rest-api-python package must be installed and configured to enable the Python API scripts for Black Duck prior to using this script.

An API key for the Black Duck server must also be configured in the `.restconfig.json` file in the package folder.

# INSTALLATION

First install the `hub-rest-api-python` package:

    git clone https://github.com/blackducksoftware/hub-rest-api-python.git
    cd hub-rest-api-python
    pip3 install -r requirements.txt
    pip3 install .

Or 
    
    pip install blackduck
    
Then extract this GIT repo into a folder (`git clone https://github.com/matthewb66/import_manifest`).

Add the required async package:

    pip install aiohttp

Configure the hub connection in the `.restconfig.json` file within the `import_manifest` folder - example contents:

    {
      "baseurl": "https://myhub.blackducksoftware.com",
      "api_token": "YWZkOTE5NGYtNzUxYS00NDFmLWJjNzItYmYwY2VlNDIxYzUwOmE4NjNlNmEzLWRlNTItNGFiMC04YTYwLWRBBWQ2MDFlMjA0Mg==",
      "insecure": true,
      "debug": false
    }

# USAGE

The `import_manifest.py` script must be invoked with one of the 2 modes kblookup or import as shown in the usage text below:

    usage: python import_manifest [-h] {kblookup,import} ...
	
    Process or import component list into project/version

    positional arguments:
 	 {kblookup,import}  Choose operation mode
    kblookup         Process component list to find matching KB URLs & export to
                     file
    import           Import component list into specified Black Duck
                     project/version using KB URLs from supplied file

    optional arguments:
       -h, --help       show this help message and exit

## kblookup Mode

The `kblookup` mode requires a component list file as input. An optional output KB Lookup File can be specified (if not specified the default filename `kblookup.out` will be used). Additionally, an input KB Lookup File can optionally be specified which will be used to reuse previous matches, and the `-a` (or `--append`) option would ensure that all entries from the input KB Lookup File are copied to the output KB Lookup file (without this option, only components found in the component list would be output).

Note that `kblookup` mode stops at 500 components in order to stop a timeout of the API connection session (20 minutes). The script can be re-run in `kblookup` mode appending to the output KB Lookup file as many times as necessary on the same component list to match more than 500 components provided the output KB Lookup file is specified as input (`-k kbfile`).

The full list of options in `kblookup` mode can be displayed using the command:

    import_manifest.py kblookup -h

Usage for kblookup mode is:

    Usage: import_manifest kblookup [-h] [-k KBFILE] [-o OUTPUT] [-r REPLACE_PACKAGE_STRING] -c COMPONENT_FILE [-a]

Further explanation of options for kblookup mode is provided below:

    -c COMPONENT_FILE, --component_file COMPONENT_FILE
                        REQUIRED input component list file. 

    -k KBFILE, --kbfile KBFILE
                        OPTIONAL input KB Lookup file which will be used to search for components. Should be specified when kblookup mode has been used previously on a project which has changed or a similar project and you want to reduce the scan time using existing matches. 

    -o OUTPUT, --output OUTPUT
                        OPTIONAL output KB Lookup File (if not specified then the default value of kblookup.out will be used). Should be used when the script has been used previously on this project which has changed, or a similar project and you want to reduce the scan time using existing matches. Note that the file name can be the same as the -k file option; the file will be read and appended to.

    -r REPLACE_PACKAGE_STRING, --replace_package_string REPLACE_PACKAGE_STRING
                        OPTIONAL string REPLACE_PACKAGE_STRING will be stripped from the input package names (can be specified multiple times)

    -a, --append
                        OPTIONAL If specified, all records from the input KB Lookup file (specified by -k) will be copied the output KB Lookup file specified by -o (kblookup.out by default). If this option is not specified, then only entries for components in the component list will be exported to the output KB Lookup file.

## import Mode

The `import` mode requires a component list file and a KB Lookup File to be specified and will lookup the components in the KB Lookup File to add new manual components to the specified Black Duck project/version (which can be created by the script if they do not already exist subject to permissions).

The full list of options in import mode can be displayed using the command:

    import_manifest.py import -h

The usage for import mode is:

    usage: import_manifest import [-h] -k KBFILE -p PROJECT -v VERSION -c COMPONENT_FILE

Further explanation of options for import mode:

    -c COMPONENT_FILE, --component_file COMPONENT_FILE
                        REQUIRED Input component list file.

    -k KBFILE, --kbfile KBFILE
                        REQUIRED input KB Lookup file – list of KB component IDs and URLs matching manifest components, created by kblookup mode and optionally modified manually.

    -p PROJECT, --project PROJECT
                        REQUIRED Black Duck project name; if project does not exist (and API user has Global Project Creator permission) then a new project will be created.

    -v VERSION, --version VERSION
                        REQUIRED Black Duck version name; if version does not exist then new version will be created.

    -d, --delete
                        OPTIONAL Delete existing manual components from the project; if not specified then components will be added to the existing list (no deletions will be made). CAUTION will delete all components not matching the input component list.

# COMPONENT LIST FILE

This is a (required) input file which contains a list of component names and versions to be imported (one per line) separated by ‘;‘ (semicolon).

Example file contents:

    ImageMagick;6.9.10-36
    OpenEXR-tools;2.2.1
    TclCurl;7.19.6
    Tktable;2.10
    Xaw3d;1.6.3
    a2ps;4.14

The component list file is required in both modes of operation and is specified using the `-c` (or `--component_file`) option (e.g. `-c compfile`).

# KB LOOKUP FILE

This is a file which contains information about the matches for components and versions in the Black Duck KnowledgeBase.

The KB Lookup File is initially produced as an output of the `kblookup` mode (using `-o outkbfile` or `--output outkbfile`) where components are looked up in the KB automatically. The KB Lookup file can also be specified as input in `kblookup` mode using `-k inkbfile` (or `--kbfile inkbfile`) options in order to reuse existing matches from a previous `kblookup` run, stopping the search for components in the KB and speeding the process.

The KB Lookup file is required by `import` mode as input.

The KB Lookup file is intended to be manually modified after being output from the `kblookup` mode to change component matches (selecting different KB components from the automatically matched ones) or to add additional components and versions which could not be matched automatically.

Records are entered 1 per line with fields separated by ‘;’ (semi-colon) and terminated by ‘;’.

Fields on each line are described below:

        REQUIRED:
        Field 1 = Local component name;
        Field 2 = KB component name; (information only)
        Field 3 = KB component source URL; (information only)
        Field 4 = KB component URL;
        OPTIONAL:
        Field 5 = Local component version string;
        Field 6 = KB Component version URL;

(Fields 5 & 6 can be repeated in pairs)

Fields 2 and 3 are provided for information only to assist with manual assessment of the automatic KB matches found by `kblookup` mode and are not used in the matching process in `import` mode.

# Example KB Lookup File Contents

Note that EOL indicates end of line added for clarity (the characters EOL are NOT included in the file).

    ImageMagick;ImageMagick;http://www.imagemagick.org/;https://hub.blackducksoftware.com/api/components/b2168761-819b-40b7-83d4-ebabfbc7f110;6.9.10.36;https://hub.blackducksoftware.com/api/components/b2168761-819b-40b7-83d4-ebabfbc7f110/versions/7e8bc4b3-17b4-4da8-a79f-cb4cfb06de90;EOL
    OpenEXR-tools;OpenEXR;http://www.openexr.com;https://hub.blackducksoftware.com/api/components/c21b38af-0b90-48be-afe6-17cf693852d2;EOL
    TclCurl;tclcurl;http://personal.telefonica.terra.es/web/getleft/tclcurl/index.html;https://hub.blackducksoftware.com/api/components/795dae6a-452d-4902-b5a4-641b206da030;EOL
    Xaw3d;;;NO MATCH;EOL
    Tktable;tktable;http://tktable.sourceforge.net/;https://hub.blackducksoftware.com/api/components/75a17ce4-f1c7-4c68-a57a-a6f5e2d9902f;2.10;https://hub.blackducksoftware.com/api/components/75a17ce4-f1c7-4c68-a57a-a6f5e2d9902f/versions/5df458aa-0853-4684-9003-f56a1040fde9;EOL

Note that the `Xaw3d` component is shown with `NO MATCH` indicating it could not be found automatically in `kblookup` mode, so could therefore be manually modified to add component and/or version URLs manually – see below.

# Modifying the KB Lookup File

Entries marked with `NO MATCH` in field 4 indicate that the automatic match process in `kblookup` mode could not find a matching package and version in the KB. The non-matched version string should also be indicated in fields 4 and 5 for example `;4.6.12;NO VERSION MATCH;`

The KB Lookup file can be modified to manually add identified matches if required. Note that if any `NO MATCH` entries in the KB Lookup file are not modified, `import` mode will not import the associated components to the project (they will be skipped).

To identify potential component matches, a manual search can be performed within the Black Duck portal using the search dialog. For example, a search for the `xaw3d` component has been performed below:

![](https://github.com/matthewb66/import_manifest/blob/master/images/im_searchkb.png)

Clicking on a component in the returned list will browse to the component landing page:
 
![](https://github.com/matthewb66/import_manifest/blob/master/images/im_compmatch.png)

If this is a good match for the required component, the URL of the component view page in the portal (https://hubeval39.blackducksoftware.com/api/components/64b691ee-345f-4345-b2c7-ebb838c853b6 above) can be used to populate the KB Lookup File by replacing `NO MATCH` with the component URL as follows:

    Xaw3d;;;NO MATCH;

should be replaced with:

    Xaw3d;;;https://hub.blackducksoftware.com/api/components/64b691ee-345f-4345-b2c7-ebb838c853b6;

This will ensure that the import mode will use this KB component for adding new manual components in the Black Duck project, searching for the required component version within the KB component. If the component version cannot be found in the KB component, then no match will be made (and no component added to the project).

Note that it is possible to enter multiple entries for the same component name with different KB component URLs; all entries will be searched in sequence to match the required version string. For example, the following 2 lines would allow matches for 2 KB components in sequence for the same component string:

    Xaw3d;;;https://hub.blackducksoftware.com/api/components/64b691ee-345f-4345-b2c7-ebb838c853b6;
    Xaw3d;;;https://hub.blackducksoftware.com/api/components/392cc27a-548d-423e-ae6c-ee621026f104;

Explanation of how duplicate entries in the KB lookup file operate in practice:

-	Consider the component/version `xaw3d;0.6.2` which is in the input component list
-	The version string ‘0.6.2’ will be searched in the first KB component found in the KB lookup file.
    o	if found, the line will be modified to add a version match for this version:
    `Xaw3d;;;https://hub.blackducksoftware.com/api/components/64b691ee-345f-4345-b2c7-ebb838c853b6;0.6.2;https://hub.blackducksoftware.com/api/components/64b691ee-345f-4345-b2c7-ebb838c853b6/version/14498227-3e8d-471b-ab84-e4c8a5259e78;`

-	If version ‘0.6.2’ is not found in the first component, then the second KB component will be searched
    o	If found in the second KB component, then the associated component version will be added to the second line in the KB Match file.

If the required version string does not exist within the KB component, it is also possible to specify the version string and a specific version URL. For example:

1. The string `peterscomponent;1.0.6` is listed in the component list file
2. The component `peterscomponent` exists in the KB (URL = https://hub.blackducksoftware.com/api/components/b2168761-819b-40b7-83d4-ebabfbc7f110), but there is no version `1.0.6` available. However, version `1.0.3` is listed in the KB which is sufficiently close
3. The KB match output file should have a `peterscomponent` entry which looks like this:
    `peterscomponent;;;NO MATCH;1.0.6;NO VERSION MATCH;`
4. Modify the entry to add the component and version URLs for `peterscomponent` and version `1.0.3` as follows:
    `peterscomponent;;;https://hub.blackducksoftware.com/api/components/b2168761-819b-40b7-83d4-ebabfbc7f110;1.0.6;https://hub.blackducksoftware.com/api/components/b2168761-819b-40b7-83d4-ebabfbc7f110/versions/7e8bc4b3-17b4-4da8-a79f-cb4cfb06de90;`
