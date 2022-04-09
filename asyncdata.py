import aiohttp
import asyncio
# from bdscan import globals
# from bdscan import utils


def get_data_async(comps, hub):
    return asyncio.run(async_main(comps, hub))


async def async_main(comps, hub):
    # token = bd.session.auth.bearer_token
    bdurl = hub.config['baseurl']
    token = hub.token
    trustcert = hub.config['insecure']

    # Get components
    async with aiohttp.ClientSession() as session:
        compdata_tasks = []

        for comp in comps.keys():
            compdata_task = asyncio.ensure_future(async_get_compdata(comp, session, bdurl, token, trustcert))
            compdata_tasks.append(compdata_task)

        print('Getting components from KB ... ')
        # print(f'compidlist: {compidlist}')
        all_compdata = dict(await asyncio.gather(*compdata_tasks))
        await asyncio.sleep(0.25)
        print(f'DEBUG got {len(all_compdata.keys())} comps')

    if len(all_compdata.keys()) == 0:
        return None

    # Get component version URLs
    async with aiohttp.ClientSession() as session:
        verdata_tasks = []

        for comp in comps.keys():
            if comp in all_compdata.keys():
                for kbentry in all_compdata[comp]:

                    verdata_task = asyncio.ensure_future(async_get_verdata(kbentry['component'], comps[comp],
                                                                           session, bdurl, token, trustcert))
                    verdata_tasks.append(verdata_task)

        print('Getting component versions from KB ... ')
        all_verdata = dict(await asyncio.gather(*verdata_tasks))
        await asyncio.sleep(0.25)
        print(f'DEBUG got {len(all_verdata.keys())} comps')

    return all_compdata, all_verdata


async def async_get_compdata(comp, session, baseurl, token, trustcert):
    # if 'componentIdentifier' not in comp:
    #     return None, None
    #
    if trustcert:
        ssl = False
    else:
        ssl = True

    headers = {
        # 'accept': "application/vnd.blackducksoftware.component-detail-4+json",
        'Authorization': f'Bearer {token}',
    }

    params = {
        # 'q': [comp['componentIdentifier']],
        'q': comp,
        'limit': 20
    }
    # search_results = bd.get_items('/api/components', params=params)
    # /api/search/components?q=name:{}&limit={}
    try:
        async with session.get(baseurl + '/api/search/components', headers=headers, params=params, ssl=ssl) as resp:
            found_comps = await resp.json()
    except Exception as e:
        return None, None

    # print('----')
    # print(baseurl + '/api/components?q=' + compid)
    # print(found_comps)
    if 'items' in found_comps and len(found_comps['items']) == 1 and 'hits' in found_comps['items'][0]:
        found = found_comps['items'][0]['hits']
        print(f"Processing {comp} - returned {len(found)}")
        return comp, found

    return None, None
    # return comp['componentIdentifier'], [found['variant'] + '/upgrade-guidance', found['component'] + '/versions']


async def async_get_verdata(compurl, ver, session, baseurl, token, trustcert):
    if trustcert:
        ssl = False
    else:
        ssl = True

    headers = {
        # 'accept': "application/vnd.blackducksoftware.component-detail-4+json",
        'Authorization': f'Bearer {token}',
    }

    # params = {
    #     # 'q': f'versionName:{ver}',
    #     'limit': 10
    # }
    # async with session.get(compurl + f'/versions?q=versionName:{ver}&limit=10', headers=headers, params=params, ssl=ssl) as resp:
    async with session.get(compurl + f'/versions?q=versionName:{ver}&limit=10', headers=headers, ssl=ssl) as resp:
            kbcomp = await resp.json()

    print(f"{compurl}: {kbcomp['totalCount']}")

    if kbcomp['totalCount'] > 0:
        vers = {}
        for item in kbcomp['items']:
            vers[item['versionName']] = item
        return(f"{compurl}", vers)
    return None, None