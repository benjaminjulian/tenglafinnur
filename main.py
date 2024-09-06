import requests
import re
import os
import json
from dotenv import load_dotenv
import base64
from urllib.parse import urlparse
import argparse

tmp_dir = 'tmp'
tmp_files_dir = os.path.join(tmp_dir, 'files')
codes_json = os.path.join(tmp_dir, 'codes.json')
vector_json = os.path.join(tmp_dir, 'vector.json')

def get_broken_links():
    if not os.path.exists(codes_json):
        return False
    with open(codes_json) as f:
        code_set = json.load(f)
    return code_set

def crawl(url):
    _l = urlparse(url)
    base = f'{_l.scheme}://{_l.netloc}'
    if base[-1] == '/':
        base = base[:-1]
    working_url = _l.geturl()
    if working_url[-1] == '/':
        working_url = working_url[:-1]

    try:
        with open(vector_json) as f:
            vector = json.load(f)
    except:
        vector = {'to-do': [], 'done': []}

    if len(vector['to-do']) == 0:
        vector['to-do'].append({'url': working_url, 'found_on': ''})
    
    try:
        with open(codes_json) as f:
            code_set = json.load(f)
    except:
        code_set = {}
    
    every_20th = 0

    try:
        while len(vector['to-do']) > 0:
            tmp_url_dict = vector['to-do'].pop(0)
            header = {'User-Agent': 'Mozilla/5.0'}
            try:
                response = requests.get(tmp_url_dict['url'], headers=header)
            except Exception as e:
                if 'error' not in code_set:
                    code_set['error'] = []
                if tmp_url_dict['url'] not in code_set['error']:
                    code_set['error'].append({'url': tmp_url_dict['url'], 'found_on': tmp_url_dict['found_on']})
                vector['done'].append(tmp_url_dict['url'])
                continue

            print(tmp_url_dict['url'][:20] + '...' + tmp_url_dict['url'][-20:], '-eftir:', len(vector['to-do']), '-búið:', len(vector['done']), '-404:', len(code_set['code404'] if 'code404' in code_set else []), ' '*8, end='\r')

            code = 'code' + str(response.status_code)

            if response.status_code != 200:
                if code not in code_set:
                    code_set[code] = []
                code_set[code].append({'url': tmp_url_dict['url'], 'found_on': tmp_url_dict['found_on']})
            
            if response.status_code == 200:
                if working_url in tmp_url_dict['url']:
                    # only check for links if this isn't a pdf, jpg, jpeg, png
                    if not (tmp_url_dict['url'][-3:] in ['.js'] or tmp_url_dict['url'][-4:] in ['.jpg', '.pdf', '.png', '.css'] or tmp_url_dict['url'][-5:] in ['.jpeg']):
                        links = re.findall(r'href=[\'"]?([^\'" >]+)', response.text)
                        links = [x.split('#')[0] for x in links]
                        links = [x for x in links if len(x) > 0]
                        # if link starts with //, add https: in front
                        links = ['https:' + x if x[:2] == '//' else x for x in links]
                        # remove mailto, tel, javascript and other protocols
                        links = [x for x in links if x[:4] != 'tel:' and x[:7] != 'mailto:' and x[:11] != 'javascript:']
                        links = list(set(links))
                        
                        for link in links:
                            # make relative links starting with / absolute w.r.t. base and without / absolute w.r.t. working_url
                            if link[0] == '/':
                                link = base + link
                            elif link[:4] != 'http':
                                link = working_url + '/' + link

                            if link not in [x['url'] for x in vector['to-do']] and link not in vector['done']:
                                vector['to-do'].append({'url': link, 'found_on': tmp_url_dict['url']})
            
            if tmp_url_dict['url'] not in vector['done']:
                vector['done'].append(tmp_url_dict['url'])
            
            every_20th += 1
            if every_20th == 20:
                every_20th = 0
                save_crawl_progress(code_set, vector)
    except KeyboardInterrupt:
        print('\nStöðva vinnslu.')
        save_crawl_progress(code_set, vector)
        exit()

def save_crawl_progress(code_set, vector):
    with open(codes_json, 'w') as f:
        json.dump(code_set, f, indent=4)
    with open(vector_json, 'w') as f:
        json.dump(vector, f, indent=4)

def get_files(dir):
    print('Sæki skráalista úr möppunni...')
    # find all files in dir recursively and list them
    files = []
    for root, dirs, filenames in os.walk(dir):
        for filename in filenames:
            files.append({'path': os.path.join(root, filename), 'name': filename})
    return files

def update_page(page, file, link, upload=False):
    _l = urlparse(page)
    base = f'{_l.scheme}://{_l.netloc}'

    if page[-1:] == '/':
        page = page[:-1]
    slug = page.split('/')[-1]

    wp_user = os.getenv('WP_USER')
    wp_pass = os.getenv('WP_PASS')

    credentials = f"{wp_user}:{wp_pass}"
    token = base64.b64encode(credentials.encode())
    headers = {'Authorization': f'Basic {token.decode("utf-8")}'}

    if upload:
        # upload file to wordpress
        with open(file, 'rb') as f:
            file_data = f.read()
        data = {
            'file': file_data,
            'title': file
        }
        response = requests.post(f'{base}/wp-json/wp/v2/media', headers=headers, files={'file': (file, file_data)})
        if response.status_code == 201:
            file = response.json()['source_url']
        else:
            print('Ekki tókst að hlaða upp skrá:')
            print('-->', file)
            return False

    # Get the page ID first
    response = requests.get(f'{base}/wp-json/wp/v2/pages?slug={slug}', headers=headers)
    pages = response.json()
    if len(pages) == 0:
        print('Síðan fannst ekki:')
        print('-->', page)
        return False
    
    for p in pages:
        page_id = p['id']
        page_content = p['content']['rendered']
        page_content = page_content.replace(link, file)
        # also replace relative links
        parsed_link = urlparse(link)
        parsed_file = urlparse(file)
        if parsed_link.netloc == parsed_file.netloc:
            page_content = page_content.replace(parsed_link.path, parsed_file.path)
        
        data = {
            'content': page_content
        }
        # Use PUT request to update the existing page
        response = requests.put(f'{base}/wp-json/wp/v2/pages/{page_id}', headers=headers, json=data)
        if response.status_code == 200:
            return True
        else:
            return False

def remove_url(url):
    try:
        with open(codes_json) as f:
            code_set = json.load(f)
        for key in code_set:
            for item in code_set[key]:
                if item['url'] == url:
                    code_set[key].remove(item)
        with open(codes_json, 'w') as f:
            json.dump(code_set, f, indent=4)
    except:
        if input('Villa við að fjarlægja tengil úr vinnsluskránni. Halda áfram (j/n)? ').lower() != 'j':
            exit()

def update_all(dir = None, wp = False, vef = False):
    if dir:
        f = get_files(dir)
        f_names = [x['name'] for x in f]
        print(len(f), 'skrár fundust í möppunni.')
    
    if wp:
        m = get_wp_media()
        m_names = [x['file'] for x in m]
        print(len(m), 'skrár fundust í WP gagnasafninu.')
    
    l = get_broken_links()
    if l:
        l_names = [x['url'] for x in l['code404']]
        l_names = [x.split('/')[-1] for x in l_names]
        print('Dauðir tenglar eru', len(l['code404']), 'talsins.')
    else:
        print('Engir brotnir tenglar fundust. (Áttu eftir að skima síðuna?)')
        return

    fix_count = 0

    for link in l_names:
        if wp:
            if link in m_names:
                if m_names.count(link) > 1:
                    dupli_page = [x['found_on'] for x in l['code404'] if x['url'].split('/')[-1] == link]
                    dupli_url = [x['url'] for x in l['code404'] if x['url'].split('/')[-1] == link]
                    dupli_file = [x['url'] for x in m if x['file'] == link]
                    for d_p in dupli_page:
                        print('Samnafna skrár fundnar:', link)
                        print('Tengillinn á hana er hér:', d_p)
                        print('Veldu réttu skrána (x til að sleppa):')
                        for i, d_f in enumerate(dupli_file):
                            print(i+1, d_f)
                        user_input = input('> ').strip()
                        try:
                            user_input = int(user_input)
                            if update_page(d_p, dupli_file[user_input-1], dupli_url[dupli_page.index(d_p)]):
                                fix_count += 1
                                remove_url(dupli_url[dupli_page.index(d_p)])
                                continue
                        except:
                            pass
                else:
                    if update_page(l['code404'][l_names.index(link)]['found_on'], m[m_names.index(link)]['url'], l['code404'][l_names.index(link)]['url']):
                        fix_count += 1
                        remove_url(l['code404'][l_names.index(link)]['url'])
                        continue
        if dir:
            if link in f_names:
                if f_names.count(link) > 1:
                    # print both file paths and offer 1), 2), 3) etc. as options for user to choose
                    dupli_page = [x['found_on'] for x in l['code404'] if x['url'].split('/')[-1] == link]
                    dupli_url = [x['url'] for x in l['code404'] if x['url'].split('/')[-1] == link]
                    dupli_file = [x['path'] for x in f if x['name'] == link]
                    for d_p in dupli_page:
                        print('Samnafna skrár fundnar:', link)
                        print('Tengillinn á hana er hér:', d_p)
                        print('Veldu réttu skrána (x til að sleppa):')
                        for i, d_f in enumerate(dupli_file):
                            print(i+1, d_f)
                        user_input = input('> ').strip()
                        try:
                            user_input = int(user_input)
                            if update_page(d_p, dupli_file[user_input-1], dupli_url[dupli_page.index(d_p)], upload=True):
                                fix_count += 1
                                remove_url(dupli_url[dupli_page.index(d_p)])
                                continue
                        except:
                            pass
                else:
                    if update_page(l['code404'][l_names.index(link)]['found_on'], f[f_names.index(link)]['path'], l['code404'][l_names.index(link)]['url'], upload=True):
                        fix_count += 1
                        remove_url(l['code404'][l_names.index(link)]['url'])
                        continue
        if vef:
            if os.getenv('BASE_URL') in l['code404'][l_names.index(link)]['url']:
                print('archive:', l['code404'][l_names.index(link)]['url'])
                archived_file = fetch_archived(l['code404'][l_names.index(link)]['url'])
                if archived_file:
                    if update_page(l['code404'][l_names.index(link)]['found_on'], archived_file, l['code404'][l_names.index(link)]['url'], upload=True):
                        fix_count += 1
                        remove_url(l['code404'][l_names.index(link)]['url'])
                        continue
        print(fix_count, 'tenglar lagaðir.', end='\r')
    print('\nKeyrslu lokið.')

def get_wp_media():
    media = []
    base = os.getenv('BASE_URL')
    endpoint = f'{base}/wp-json/wp/v2/media'

    page = 1

    while True:
        params = {
            'per_page': 100,
            'page': page
        }
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            media_items = response.json()
            for item in media_items:
                media.append({'url': item['source_url'], 'file': item['source_url'].split('/')[-1]})
        
        if len(media_items) < 100:
            break
        page += 1
    return media

def fetch_archived(url):
    archive_url = 'https://vefsafn.is/is/' + url
    response = requests.get(archive_url)
    if response.status_code == 200:
        timestamp = re.findall(r'"request_ts": "(\d+)"', response.text)[0]
        archived_file_url = f'https://vefsafn.is/{timestamp}mp_/{url}'
        response = requests.get(archived_file_url)
        if response.status_code == 200:
            if not os.path.exists(tmp_files_dir):
                os.makedirs(tmp_files_dir)
            with open(os.path.join(tmp_files_dir, url.split('/')[-1]), 'wb') as f:
                f.write(response.content)
            return os.path.join(tmp_files_dir, url.split('/')[-1])
    return False

class IcelandicArgumentDefaultsHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ', '.join(action.option_strings) + ' ' + args_string

def main(args):
    load_dotenv()

    _base_ =args.vefur
    # make it a proper https
    if _base_[:4] != 'http':
        _base_ = 'https://' + _base_
    os.environ['BASE_URL'] = _base_

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    if args.skima:
        crawl(_base_)
    
    if args.media or args.vefsafn or args.mappa:
        update_all(args.mappa, args.media, args.vefsafn)

if __name__ == '__main__':
    # parse arguments
    parser = argparse.ArgumentParser(description='Þessi kóði uppfærir brotna tengla á WordPress.', formatter_class=IcelandicArgumentDefaultsHelpFormatter)
    parser.add_argument('vefur', type=str, help='vefsíðan sem unnið er á')
    parser.add_argument('--skima', action='store_true', help='skima vefsíðuna')
    parser.add_argument('--media', action='store_true', help='reyna að tengja skrár með sömu nöfnum úr WP gagnasafninu')
    parser.add_argument('--vefsafn', action='store_true', help='reyna að ná í gögn frá Vefsafninu')
    parser.add_argument('--mappa', type=str, help='hlaða upp skrám úr möppu sem hafa sömu nöfn og brotnir tenglar')

    parser._positionals.title = 'Nauðsynlegar breytur'
    parser._optionals.title = 'Stýribreytur'
    parser._actions[0].help = 'sýna þessi hjálparskilaboð og hætta'

    args = parser.parse_args()
    
    main(args)