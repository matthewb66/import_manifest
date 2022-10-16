#!/usr/bin/env python
#
# This script operates in 2 modes as follows:
# 1. Mode kblookup: Accept input file, read list of components & versions from the file, producing an output list of
# BD URLs for KB components which match the component
#    name and version
# 2. Mode import: Accept input file, seed file, project name and version - Read list of components & version from
# the input file in addition to a seed file of BD URLs (produced by mode 1), find matching KB component & version
# and (if not already in project) add as manual component to specified project & version

import argparse
# import json
import logging
import re
from difflib import SequenceMatcher
import os
import sys
import time

# from import_manifest import asyncdata
import asyncdata

from blackduck.HubRestApi import HubInstance

import_manifest_version = '1.1'

logging.basicConfig(filename='../import_manifest.log', level=logging.DEBUG)

hub = HubInstance()
comps_postlist = []


def get_kb_component(packagename):
    # print("DEBUG: processing package {}".format(packagename))
    packagename = packagename.replace(" ", "+")
    # packagename = packagename.replace("-", "+")
    # req_url = hub.get_urlbase() + "/api/search/components?q=name:{}&limit={}".format(packagename, 20)
    req_url = hub.get_urlbase() + "/api/search/components?q=name:{}&limit={}".format(packagename, 20)
    try:
        response = hub.execute_get(req_url)
        if response.status_code != 200:
            logging.error("Failed to retrieve KB matches, status code: {response.status_code}")
        return response
    except:
        logging.error("get_kb_component(): Exception trying to find KB matches")
    return None


def find_ver_from_compver(kburl, version, compdata, allverdata):
    matchversion = ""
    
    # component = hub.execute_get(kburl)
    # if component.status_code != 200:
    #     logging.error("Failed to retrieve component, status code: {}".format(component.status_code))
    #     return "", "", 0, "", ""
    # bdcomp_sourceurl = component.json().get('url')
    # if bdcomp_sourceurl:
    #     bdcomp_sourceurl = bdcomp_sourceurl.replace(';','')
    # #
    # # Request the list of versions for this component
    # compname = component.json().get('name')
    # respitems = component.json().get('_meta')
    # links = respitems['links']
    # vers_url = links[0]['href'] + "?limit=1000"
    # kbversions = hub.execute_get(vers_url)
    # if kbversions.status_code != 200:
    #     logging.error("Failed to retrieve component, status code: {}".format(kbversions.status_code))
    #     return "", "", 0, "", ""

    bdcomp_sourceurl = ''

    compname = ''
    matchstrength = 0
    kbver_url = ''

    if kburl in allverdata.keys():
        localversion = version.replace('-', '.')
        for kbver in allverdata[kburl].keys():
            ver_entry = allverdata[kburl][kbver]
            compname = ver_entry['compName']
            kbver_url = ver_entry['_meta']['href']
            if 'fields' in compdata and 'url' in compdata['fields']:
                bdcomp_sourceurl = compdata['fields']['url'][0]

            # logging.debug("DEBUG: component = {} searchversion = {} kbver = {} kbverurl = {}".format(compname,
            # version, kbversionname, kbver_url))
            if kbver == localversion:
                # exact version string match
                matchversion = ver_entry['versionName']
                matchstrength = 3
                break
            kbversionname = kbver.replace('-', '.')

            # Need to look for partial matches
            seq = SequenceMatcher(None, kbversionname, localversion)
            match = seq.find_longest_match(0, len(kbversionname), 0, len(localversion))
            if (match.a == 0) and (match.b == 0) and (match.size == len(kbversionname)):
                # Found match of full kbversion at start of search_version
                if len(kbversionname) > len(matchversion):
                    # Update if the kbversion is longer than the previous match
                    matchversion = ver_entry['versionName']
                    matchstrength = 2
                    logging.debug("Found component block 1 - version=" + matchversion)

            elif (match.b == 0) and (match.size == len(localversion)):
                # Found match of full search_version within kbversion
                # Need to check if kbversion has digits before the match (would mean a mismatch)
                mob = re.search("\d", kbversionname[0:match.a])
                if not mob and (len(kbversionname) > len(matchversion)):
                    # new version string matches kbversion but with characters before and is longer than the
                    # previous match
                    matchversion = ver_entry['versionName']
                    logging.debug("Found component block 2 - version=" + matchversion)
                    if (match.a == 1) and (kbversionname.lower() == 'v'):  # Special case of kbversion starting 'v'
                        matchstrength = 3
                    else:
                        matchstrength = 2

            elif (match.a == 0) and (match.b == 0) and (match.size > 2):
                # both strings match at start for more than 2 characters min
                # Need to try close numeric version match
                # - Get the final segment of searchversion & kbversion
                # - Match if 2 versions off?
                if 0 <= match.size - localversion.rfind(".") <= 2:
                    # common matched string length is after final .
                    kbfinalsegment = kbversionname.split(".")[-1]
                    localfinalsegment = localversion.split(".")[-1]
                    if kbfinalsegment.isdigit() and localfinalsegment.isdigit():
                        # both final segments are numeric
                        logging.debug("kbfinalsegment = " + kbfinalsegment + " localfinalsegment = " +
                                      localfinalsegment + " matchversion = " + matchversion)
                        if abs(int(kbfinalsegment) - int(localfinalsegment)) <= 2:
                            # values of final segments are within 2 of each other
                            if len(kbversionname) >= len(matchversion):
                                # kbversion is longer or equal to matched version string
                                matchversion = ver_entry['versionName']
                                matchstrength = 1
                                logging.debug(f"Found component block 3 - version={matchversion}")
                                  
        if matchversion != "":
            return compname, matchversion, matchstrength, bdcomp_sourceurl, kbver_url
            # return matchversion, matchstrength, kbver_url

    return "", "", 0, "", ""


def find_ver_from_hits(hits, search_version, allcompdata, allverdata):
    matchversion = ""
    matchstrength = 0
    for hit in hits:
        #
        # Get component from URL
        comp_url = hit['_meta']['href']
        # matchversion, matchstrength, bdcompver_url = \
        compname, matchversion, matchstrength, bdcomp_sourceurl, bdcompver_url = \
            find_ver_from_compver(comp_url, search_version, hit, allverdata)
        if matchstrength == 3:
            break

    if matchversion == "":
        return "", "", 0, "", "", ""
    else:
        return compname, matchversion, matchstrength, bdcomp_sourceurl, comp_url, bdcompver_url


def search_kbpackage(package, allcompdata):
    # response = get_kb_component(package)
    # if response.status_code != 200:
    #     print("error")
    #     return ""
    #
    # respitems = response.json().get('items', [])
    # logging.debug("{} items returned".format(respitems[0]['searchResultStatistics']['numResultsInThisPage']))
    # if respitems[0]['searchResultStatistics']['numResultsInThisPage'] > 0:
    #     return respitems[0]['hits']
    # else:
    #     return ""
    if package in allcompdata.keys():
        return allcompdata[package]
    else:
        return ''


def find_comp_from_kb(compstring, version, outkbfile, inkbfile, replace_strings, allcompdata, allverdata):
    #
    # Try to find component in KB
    #
    end = False
    found_comp = ""
    found_version = ""
    comp_url = ""
    compver_url = ""
    source_url = ""
    max_matchstrength = 0

    # packagename = package.lower()
    if replace_strings:
        for repstr in replace_strings:
            compname = compstring.replace(repstr, '')
    else:
        compname = compstring
        
    origcomp = compname
    while not end:
        logging.debug("find_comp_from_kb(): Searching for '{}'".format(compname))
        hits = search_kbpackage(compname, allcompdata)
        if hits:
            logging.debug("find_comp_from_kb(): Found matches for package {}".format(compname))
            temp_comp, temp_version, matchstrength, temp_srcurl, temp_compurl, temp_compverurl = \
                find_ver_from_hits(hits, version, allcompdata, allverdata)
            if matchstrength == 3:
                end = True
            if matchstrength > max_matchstrength:
                max_matchstrength = matchstrength
                found_comp = temp_comp
                found_version = temp_version
                comp_url = temp_compurl
                compver_url = temp_compverurl
                source_url = temp_srcurl             
                
        if not end and (len(compname) == len(origcomp)) and (compname.find("-") > -1):
            compnamecolons = compname.replace("-", "::")
            compnamecolons = compnamecolons.replace("_", "::")
            hits = search_kbpackage(compnamecolons, allcompdata)
            if hits:
                logging.debug("find_comp_from_kb(): Found matches for package {}".format(compnamecolons))
                temp_comp, temp_version, matchstrength, temp_srcurl, temp_compurl, temp_compverurl = \
                    find_ver_from_hits(hits, version, allcompdata, allverdata)
                if matchstrength == 3:
                    end = True    
                if matchstrength > max_matchstrength:
                    max_matchstrength = matchstrength
                    found_comp = temp_comp
                    found_version = temp_version
                    comp_url = temp_compurl
                    compver_url = temp_compverurl
                    source_url = temp_srcurl                

        if not end and ((compname.find("-") > -1) or (compname.find("_") > -1)):
            #
            # Process component replacing - with spaces
            compnamespaces = compname.replace("-", " ")
            compnamespaces = compnamespaces.replace("_", " ")
            hits = search_kbpackage(compnamespaces, allcompdata)
            if hits:
                logging.debug("find_comp_from_kb(): Found matches for package {}".format(compnamespaces))
                temp_comp, temp_version, matchstrength, temp_srcurl, temp_compurl, temp_compverurl = \
                    find_ver_from_hits(hits, version, allcompdata, allverdata)
                if matchstrength == 3:
                    end = True
                if matchstrength > max_matchstrength:
                    max_matchstrength = matchstrength
                    found_comp = temp_comp
                    found_version = temp_version
                    comp_url = temp_compurl
                    compver_url = temp_compverurl
                    source_url = temp_srcurl             

        if not end:
            #
            # Remove trailing -xxx from package name
            newcompname = compname.rsplit("-", 1)[0]
            if len(newcompname) == len(compname):
                #
                # No - found, try removing trailing .xxxx
                newcompname = compname.rsplit(".", 1)[0]
                if len(newcompname) == len(compname):
                    end = True
            compname = newcompname

    if max_matchstrength > 0:
        print(f" - MATCHED '{found_comp}/{found_version}' (sourceURL={source_url})")
        return f"{compstring};{found_comp};{source_url};{comp_url};{version};{compver_url};\n"

    else:
        print(" - NO MATCH")
        return f"{compstring};;;NO MATCH;{version};NO VERSION MATCH;\n"


def add_kbfile_entry(outkbfile, line):
    try:
        ofile = open(outkbfile, "a+")
    except Exception as e:
        logging.error("append_kbfile(): Failed to open file {} for read".format(outkbfile))
        return

    ofile.write(line)
    ofile.close()
    

def update_kbfile_entry(outkbfile, package, version, compurl, kbverurl):
    #
    # Append version strings to kbfile entry
    #
    # FIELDS:
    # 1 = Local component name;
    # 2 = KB component name;
    # 3 = KB component source URL;
    # 4 = KB component URL;
    # 
    # OPTIONAL:
    # 5 = Local component version string
    # 6 = KB Component version URL
    # (Repeated as often as matched)
    try:
        ofile = open(outkbfile, "r")
    except Exception as e:
        logging.error("update_kbfile(): Failed to open file {} for read".format(outkbfile))
        return

    lines = ofile.readlines()
    ofile.close()

    try:
        ofile = open(outkbfile, "w")
    except Exception as e:
        logging.error("update_kbfile(): Failed to open file {} for write".format(outkbfile))
        return
    
    for line in lines:
        elements = line.split(";")
        compname = elements[0]
        thiscompurl = elements[3]
        if compname != package:
            ofile.write(line)
        else:
            if compurl != thiscompurl:
                ofile.write(line)
            else:
                ofile.write("{}{};{};\n".format(line.rstrip(), version, kbverurl))
                logging.debug("update_kbfile(): updated kbfile line with '{};{};'".format(version, kbverurl))
            
    ofile.close()
    return


def import_kbfile(kbfile, outfile):
    #
    # If outfile is not "" then copy kbfile to outfile
    #
    # FIELDS:
    # 1 = Local component name;
    # 2 = KB component name;
    # 3 = KB component source URL;
    # 4 = KB component URL;
    # 
    # OPTIONAL:
    # 5 = Local component version string
    # 6 = KB Component version URL
    # (Repeated as often as matched)
    
    kblookupdict = {}
    kbverdict = {}
    output = False
    try:
        kfile = open(kbfile, "r")
    except Exception as e:
        logging.error(f"import_kbfile(): Failed to open file '{kbfile}'")
        return kblookupdict, kbverdict
    
    print(f"Using KB match list input file '{kbfile}'")
    if outfile != "" and outfile != kbfile:
        output = True
        try:
            ofile = open(outfile, "a+")
            print(f"Will write to KB match list output file '{outfile}'")
        except:
            logging.error(f"import_kbfile(): Failed to open file '{outfile}' ")
            return "", ""
    
    lines = kfile.readlines()
    
    count = 0
    for line in lines:
        elements = line.split(";")
        compname = elements[0]
        kbcompurl = elements[3]
        # if kbcompurl != "NO MATCH":
        # kblookupdict[compname] = kbcompurl
        kblookupdict.setdefault(compname, []).append(kbcompurl)
        index = 4
        while index < len(elements) - 1:
            kbverdict[compname + "/" + elements[index]] = elements[index+1]
            index += 2
        #elif kbcompurl == "NO MATCH":
        #    kblookupdict.setdefault(compname, []).append("NO MATCH")
        count += 1
        if output:
            ofile.write(line)
    
    kfile.close()
    if output:
        ofile.close()
        
    print(f"Processed {count} entries from '{kbfile}'")
    return kblookupdict, kbverdict


def find_compver_from_compurl(package, kburl, search_version, all_compdata, all_verdata):
    compname, matchversion, matchstrength, bdcomp_sourceurl, bd_verurl = \
        find_ver_from_compver(kburl, search_version, all_compdata, all_verdata)
    if matchstrength > 0:
        return bd_verurl, bdcomp_sourceurl
    else:
        return "NO VERSION MATCH", ""


def set_comp_postdata(kbverurl, compfile, compver):
    # posturl = bdverurl + "/components"
    # custom_headers = {
    #         'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-6+json'
    # }
    
    return {
            "component": kbverurl,
            "componentPurpose": "import_manifest: imported from file " + compfile,
            "componentModified": False,
            "componentModification": "Original component = " + compver
    }


def del_comp_from_bom(projverurl, compurl):
    # CURLURL="${HUBURL}/api/v1/releases/${PROJVERID}/component-bom-entries"
    # [{"entityKey":{"entityId":"76a3c684-639b-4675-ac98-fbec8847539b","entityType":"RL"}}]
    # curl $CURLOPTS -X DELETE -H "Accept: application/json" -H "Content-type: application/json" --header
    # "Authorization: Bearer $TOKEN" "${CURLURL//[\"]}" \
    # -d "[{\"entityKey\":{\"entityId\":\"${KBVERID}\",\"entityType\":\"RL\"}}]"

    # https://hubeval39.blackducksoftware.com/api/projects/e5de5955-67c1-4b03-911b-5f87f4a0a367/versions/586a2bc7-a1a3-
    # 4c58-993d-4d1ba6fa301b/components/339bcb81-ac9a-43f3-b293-8f20a84b79ed/versions/f2e2358c-3e41-43ba-bb6c-
    # e2089c4424b5
    # https://hubeval39.blackducksoftware.com/api/components/55da34b1-ebc5-4bc3-8440-e38c95bf5145/versions/83e168cb-
    # 75c6-481a-80a3-f5aaaf8ea7c0
    
    # response = hub.execute_delete(compurl)

    # delurl = "/".join(projverurl.split("/")[:2]) + "/api/v1/releases/" + projverurl.split("/")[7] + "/component-bom-
    # entries"
    # kbverid = compurl.split("/")[7]
    # postdata =  { "entityKey":{"entityId":kbverid,"entityType":"RL"}}
    
    response = hub.execute_delete(compurl)
    if response.status_code == 200:
        logging.debug("Component deleted {}".format(compurl))
        return True
    else:
        logging.error("Component NOT deleted {}".format(compurl))
        return False


def manage_project_version(hub, proj, ver):
    bdproject = hub.get_project_by_name(proj)
    if not bdproject:
        resp = hub.create_project(proj, ver)
        if resp.status_code != 201:
            logging.debug(f"Cannot create project '{proj}'")
            return None, None
        
        print(f"Created project '{proj}'")
        bdproject = hub.get_project_by_name(proj)
    else:
        print(f"Found project '{proj}'")
        
    bdversion = hub.get_version_by_name(bdproject, ver)
    if not bdversion:
        resp = hub.create_project_version(bdproject, ver)
        if resp.status_code != 201:
            logging.debug(f"Cannot create project version {ver}")
            return None, None
        print(f"Created version '{ver}'")
        time.sleep(1)
        bdversion = hub.get_version_by_name(bdproject, ver)
    else:
        print(f"Found version '{ver}'")
    return bdproject, bdversion


def read_compfile(compfile):
    try:
        cfile = open(compfile)
    except:
        logging.error("Failed to open file {} ".format(compfile))
        return None
    
    if cfile.mode != 'r':
        logging.error("Failed to open file {} ".format(compfile))
        return None

    lines = cfile.readlines()
#
# Alternative file format:
#    outlines = []
#    package = ""
#    version = ""
#    for line in lines:
#        splitline = line.split(":")
#        if splitline[0] == "PACKAGE NAME":
#            package = splitline[1].strip()
#        if splitline[0] == "PACKAGE VERSION":
#            version = splitline[1].strip()
#        if splitline[0] == "LICENSE":
#            if splitline[1].strip() == "CLOSED":
#                continue
#            else:
#                outlines.append("{};{}".format(package, version))
#    lines = outlines
#
# End Alternative
                
    return lines


def process_compfile_line(line):
    # version = ""
    # package = ""
    # # splitline = line.split("-")
    # # for segment in splitline:
    # #     if segment[0].isdigit():
    # #         if version != "":
    # #             version += "."
    # #         version += segment.strip()
    # #     else:
    # #         if package != "":
    # #             package += "-"
    # #         package += segment.strip()
    # # return(package, version)

    splitline = line.rstrip().split(";")  # Alternative import
    if len(splitline) > 1:
        return splitline[0], splitline[1]  # Alternative import
    else:
        print('WARN: Invalid line in compfile')
        return '', ''

#
# Main Program
            

print(f"BD-import-manifest utility - version {import_manifest_version}")

parser = argparse.ArgumentParser(description='Process or import component list into Black Duck project/version',
                                 prog='bd-import-manifest')

subparsers = parser.add_subparsers(help='Choose operation mode', dest='command')
# create the parser for the "kblookup" command
parser_g = subparsers.add_parser('kblookup', help='Process component list to find matching KB URLs & export to file')
parser_g.add_argument('-c', '--component_file', help='Input component list file', required=True)
parser_g.add_argument('-k', '--kbfile', help='Input file of KB component IDs matching manifest components')
parser_g.add_argument('-o', '--output', help='Output file of KB component IDs matching manifest components '
                                             '(default "kblookup.out")', default='kblookup.out')
parser_g.add_argument('-r', '--replace_package_string', help='Replace (remove) string in input package name',
                      action='append')
parser_g.add_argument('-a', '--append', help='Append new KB URLs to the KB Lookup file specified in -k',
                      action='store_true')
parser_g.add_argument('-s', '--strict', help='Only match components with exact name', action='store_true')

# create the parser for the "import" command
parser_i = subparsers.add_parser('import', help='Import component list into specified Black Duck project/version using '
                                                'KB URLs from supplied file')
parser_i.add_argument('-c', '--component_file', help='Input component list file', required=True)
parser_i.add_argument('-k', '--kbfile', help='Input file of KB component IDs and URLs matching manifest components',
                      required=True)
parser_i.add_argument('-p', '--project', help='Black Duck project name', required=True)
parser_i.add_argument('-v', '--version', help='Black Duck version name', required=True)
parser_i.add_argument('-d', '--delete', help='Delete existing manual components from the project - if not specified '
                                             'then components will be added to the existing list', action='store_true')

# parser.add_argument("version")
args = parser.parse_args()


def main():
    kblookupdict = {}   # Dict of package names from kbfile with matching array of component URLs for each
    kbverdict = {}      # Dict of package/version strings with single component version URL for each
    existing_compdict = {}  # Dict of manually added components for optional deletion is -d specified

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.kbfile and not os.path.exists(args.kbfile):
        print(f"Input KB Lookup file '{args.kbfile}' does not exist - exiting")
        sys.exit(1)

    if not os.path.exists(args.component_file):
        print(f"Component file {args.component_file} does not exist - exiting")
        sys.exit(1)

    if args.command == 'kblookup':
        if os.path.exists(args.output) and not args.append:
            print(f'KB Lookup output file {args.output} already exists - please use -a option if you wish to append')
            sys.exit(1)

        if args.kbfile:
            if args.output:
                kblookupdict, kbverdict = import_kbfile(args.kbfile, args.output)
            else:
                kblookupdict, kbverdict = import_kbfile(args.kbfile, "")

        #
        # Process components to find matching KB URLs - output to componentlookup.csv
        lines = read_compfile(args.component_file)

        print("")
        print(f"Pre-processing component list file '{args.component_file}' to find matching KB entries ...")
        pkgs = {}
        for line in lines:
            package, version = process_compfile_line(line)

            if package not in kblookupdict:
                packverstr = package + "/" + version
                if packverstr not in kbverdict:
                    if args.replace_package_string:
                        for repstr in args.replace_package_string:
                            package = package.replace(repstr, '')

                    pkgs[package] = version
            elif kblookupdict[package][0] == "NO MATCH":
                pkgs[package] = version

        all_compdata, all_verdata = asyncdata.get_data_async(pkgs, hub, args.strict)

        print("")
        print(f"Will use output kbfile '{args.output}'")
        print(f"Processing component list file '{args.component_file}' ...")
        processed_comps = 0
        for line in lines:
            package, version = process_compfile_line(line)

            print(f"Manifest Component = '{package}/{version}'", end="")
            if package in kblookupdict:
                #
                # Found primary package name in kbfile
                if kblookupdict[package][0] == "NO MATCH":
                    print("- NO MATCH in input KB File")
                    continue
                logging.debug(f"Found package '{package}' in kblookupdict")
                #
                # Check if package/version is defined in KB Lookup file
                packverstr = package + "/" + version
                if packverstr in kbverdict:
                    # Found in KB ver URL list - Nothing to do
                    logging.debug(f"Found component '{package}' version '{version}' in kbverdict - "
                                  f"URL {kbverdict[packverstr]}")
                    kbverurl = kbverdict[packverstr]
                    print(" - already MATCHED in input KB file")
                else:
                    #
                    # Loop through component URLs to check for component version
                    foundkbversion = False
                    for kburl in kblookupdict[package]:
                        kbverurl, srcurl = find_compver_from_compurl(package, kburl, version, all_compdata, all_verdata)
                        processed_comps += 1
                        if kbverurl != "NO VERSION MATCH":
                            print(f" - MATCHED '{package}/{version}' (sourceURL={srcurl})")
                            #
                            # KB version URL found
                            kbverdict[package + "/" + version] = kbverurl
                            update_kbfile_entry(args.output, package, version, kblookupdict[package][0], kbverurl)
                            processed_comps += 1

                            foundkbversion = True
                            break
                    if not foundkbversion:
                        #
                        # No version match - need to add NO VERSION MATCH string to kbfile
                        update_kbfile_entry(args.output, package, version, kblookupdict[package][0], "NO VERSION MATCH")
                        continue  # move to next component
            else:
                newkbline = find_comp_from_kb(package, version, args.output, args.kbfile, args.replace_package_string,
                                              all_compdata, all_verdata)
                add_kbfile_entry(args.output, newkbline)
                processed_comps += 1

            # if processed_comps > 500:
            #     print("500 components processed - terminating. Please rerun with -k option to append to kbfile")
            #     exit()
        if processed_comps > 0:
            sys.exit(0)
        sys.exit(1)

    if args.command == 'import':
        comps_postlist = []

        print(f"Using component list file '{args.component_file}'")
        lines = read_compfile(args.component_file)

        if args.kbfile:
            kblookupdict, kbverdict = import_kbfile(args.kbfile, "")

        bdproject, bdversion = manage_project_version(hub, args.project, args.version)
        if not bdversion:
            print(f"Cannot create version '{args.version}'")
            exit()
        bdversion_url = bdversion['_meta']['href']
        components = hub.get_version_components(bdversion)
        print(f"Found {components['totalCount']} existing components in project")
        if args.delete:
            count = 0
            logging.debug(f"Looking through the components for project {args.project}, version {args.version}.")
            for component in components['items']:
                if component['matchTypes'][0] == 'MANUAL_BOM_COMPONENT':
                    existing_compdict[component['componentVersion']] = component['_meta']['href']
                    count += 1
            print(f"Found {count} manual components")

        print("")
        print("Processing component list ...")
        for line in lines:
            package, version = process_compfile_line(line)
            print(f"Checking component '{package}/{version}'", end="")
            logging.debug(f"Manifest component from compfile = '{package}/{version}'")
            kbverurl = ""
            if package in kblookupdict:
                #
                # Check if package/version is in kbverdict
                packstr = package + "/" + version
                if packstr in kbverdict:
                    #
                    # Component version URL found in kbfile
                    logging.debug(f"Compver found in kbverdict packstr = {packstr}, "
                                  f"kbverdict[packstr] = {kbverdict[packstr]}")
                    kbverurl = kbverdict[packstr]
                # else:
                #     #
                #     # No match of component version in kbfile version URLs
                #     for kburl in kblookupdict[package]:
                #         #
                #         # Loop through component URLs from kbfile
                #         kbverurl, srcurl = find_compver_from_compurl(package, kburl, version)
                #         if kbverurl != "NO VERSION MATCH":
                #             break
                if kbverurl != "NO VERSION MATCH":
                    #
                    # Component does not exist in project
                    logging.debug("Component found in project - packstr = {}".format(packstr))
                    print(f" - Found in KB Lookup file - will add to project")
                    comps_postlist.append(set_comp_postdata(kbverurl, args.component_file, package + "/" + version))
                    if kbverurl in existing_compdict.keys():
                        existing_compdict.pop(kbverurl)
                else:
                    print(" - No component match from KB Lookup file")

            else:
                print(" - No component match from KB Lookup file")

        num_comps_added = asyncdata.post_data_async(comps_postlist, hub, bdversion_url)
        print(f'{num_comps_added} Components added to project {args.project} version {args.version}')

        if args.delete:
            # print("Unused components not deleted - not available until version 2019.08 which supports the required API")
            count = 0
            for compver in existing_compdict.keys():
               del_comp_from_bom(bdversion_url, existing_compdict[compver])
               count += 1
            print(f"Deleted {count} existing manual components")

        sys.exit(0)

if __name__ == "__main__":
    main()