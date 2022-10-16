import aiohttp
import asyncio


def get_data_async(comps, hub, strict):
    return asyncio.run(async_kbcomps_main(comps, hub, strict))


async def async_kbcomps_main(comps, hub, strict):
    # token = bd.session.auth.bearer_token
    bdurl = hub.config['baseurl']
    token = hub.token
    trustcert = hub.config['insecure']

    # Get components
    async with aiohttp.ClientSession() as session:
        compdata_tasks = []

        for comp in comps.keys():
            compdata_task = asyncio.ensure_future(async_get_compdata(comp, strict, session, bdurl, token, trustcert))
            compdata_tasks.append(compdata_task)

        print('Getting components from KB ... ')
        # print(f'compidlist: {compidlist}')
        all_compdata = dict(await asyncio.gather(*compdata_tasks))
        await asyncio.sleep(0.25)
        # print(f'DEBUG got {len(all_compdata.keys())} comps')

    if len(all_compdata.keys()) == 0:
        return None

    # Get component version URLs
    async with aiohttp.ClientSession() as session:
        verdata_tasks = []

        for comp in comps.keys():
            if comp in all_compdata.keys():
                for kbentry in all_compdata[comp]:

                    verdata_task = asyncio.ensure_future(
                        async_get_verdata(kbentry['name'], kbentry['_meta']['href'], comps[comp],
                                          session, token, trustcert))
                    verdata_tasks.append(verdata_task)

        print('Getting component versions from KB:')
        all_verdata = dict(await asyncio.gather(*verdata_tasks))
        await asyncio.sleep(0.25)
        # print(f'DEBUG got {len(all_verdata.keys())} comps')

    return all_compdata, all_verdata


async def async_get_compdata(comp, strict, session, baseurl, token, trustcert):
    # if 'componentIdentifier' not in comp:
    #     return None, None
    #
    if trustcert:
        ssl = False
    else:
        ssl = True

    headers = {
        'accept': "application/vnd.blackducksoftware.internal-1+json",
        'Authorization': f'Bearer {token}',
    }

    params = {
        # 'q': [comp['componentIdentifier']],
        'q': 'name:' + comp,
        'limit': 20
    }
    # search_results = bd.get_items('/api/components', params=params)
    # /api/search/components?q=name:{}&limit={}
    try:
        async with session.get(baseurl + '/api/search/kb-components', headers=headers, params=params, ssl=ssl) as resp:
            found_comps = await resp.json()
    except Exception as e:
        return None, None

    # if 'items' in found_comps and len(found_comps['items']) == 1 and 'hits' in found_comps['items'][0]:
    #     foundlist = found_comps['items'][0]['hits']
    #     print(f"- Component '{comp}': {len(foundlist)} matches")
    #     if strict:
    #         newfoundlist = []
    #         for item in foundlist:
    #             if item['fields']['name'][0].lower() == comp.lower():
    #                 newfoundlist.append(item)
    #     else:
    #         newfoundlist = foundlist
    if 'items' in found_comps and len(found_comps['items']) > 0:
        foundlist = found_comps['items']
        print(f"- Component '{comp}': {len(foundlist)} matches")
        if strict:
            newfoundlist = []
            for item in foundlist:
                if item['name'].lower() == comp.lower():
                    newfoundlist.append(item)
        else:
            newfoundlist = foundlist

        return comp, newfoundlist

    return None, None
    # return comp['componentIdentifier'], [found['variant'] + '/upgrade-guidance', found['component'] + '/versions']


async def async_get_verdata(compname, compurl, ver, session, token, trustcert):
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
    # async with session.get(compurl + f'/versions?q=versionName:{ver}&limit=10', headers=headers, params=params,
    # ssl=ssl) as resp:
    async with session.get(compurl + f'/versions?q=versionName:{ver}&limit=5', headers=headers, ssl=ssl) as resp:
        kbcomp = await resp.json()

    # print(f"{compurl}: {kbcomp['totalCount']}")

    if kbcomp['totalCount'] > 0:
        print('.', end='')
        vers = {}
        for item in kbcomp['items']:
            thisver = item
            thisver['compName'] = compname
            vers[item['versionName']] = item
        return f"{compurl}", vers
    return None, None


def post_data_async(comps, hub, bdverurl):
    return asyncio.run(async_post_main(comps, hub, bdverurl))


async def async_post_main(comps, hub, bdverurl):
    # token = bd.session.auth.bearer_token
    # bdurl = hub.config['baseurl']
    token = hub.token
    trustcert = hub.config['insecure']

    # Get components
    async with aiohttp.ClientSession() as session:
        postdata_tasks = []

        for comp in comps:
            postdata_task = asyncio.ensure_future(async_post_compdata(comp, session, bdverurl, token, trustcert))
            postdata_tasks.append(postdata_task)

        print('\nAdding components to project ...')
        # print(f'compidlist: {compidlist}')
        all_postdata = dict(await asyncio.gather(*postdata_tasks))
        await asyncio.sleep(0.25)

    return len(all_postdata.keys())


async def async_post_compdata(comp, session, bdverurl, token, trustcert):
    # if 'componentIdentifier' not in comp:
    #     return None, None
    #
    if trustcert:
        ssl = False
    else:
        ssl = True

    headers = {
        # 'accept': "application/vnd.blackducksoftware.component-detail-4+json",
        'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-6+json',
        'Authorization': f'Bearer {token}',
    }

    # custom_headers = {
    #         'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-6+json'
    # }

    try:
        async with session.post(bdverurl + '/components', json=comp, headers=headers, ssl=ssl) as resp:
            found_comps = await resp.json()
    except Exception as e:
        print(f"Error creating component - {e}")
        return '', 1

    return comp['componentModification'], 0
    # return comp['componentIdentifier'], [found['variant'] + '/upgrade-guidance', found['component'] + '/versions']
