from lxml import etree
from os import path
import io
import random

NAMESPACES = {'XML': 'http://www.w3.org/XML/1998/namespace',
              'EPUB': 'http://www.idpf.org/2007/ops',
              'DAISY': 'http://www.daisy.org/z3986/2005/ncx/',
              'OPF': 'http://www.idpf.org/2007/opf',
              'CONTAINERS': 'urn:oasis:names:tc:opendocument:xmlns:container',
              'DC': 'http://purl.org/dc/elements/1.1/',
              'XHTML': 'http://www.w3.org/1999/xhtml'}

IMAGE_MEDIA_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml']


def paths_join_normalize(base: str, *joins: str) -> str:
    '''
    path.normcase(path.normpath(path.join(path, paths)))
    '''
    for addition in joins:
        base = path.join(base, addition)
    return path.normcase(path.normpath(base))


class MissingValueError(ValueError):
    pass


class Pathfinder:
    '''
    Object finding paths to stylesheets and files in the spine of
    the unpacked .epub file
    '''
    def __init__(self, book_dir: str = None) -> None:
        #  str -> str | list[str]
        # 'opf_file': str, 'spine': list[str], 'stylesheets': list[str]
        self._rendition = (-1,
                           {'spine': list[str](),
                            'stylesheets': list[str]()})
        self._opf_files = list[str]()
        self.set_book_dir(book_dir=book_dir)

    def set_book_dir(self, book_dir: str = None) -> None:
        self.book_dir = book_dir

    def find_renditions(self) -> None:
        self._rendition = (-1,
                           {'spine': list[str](),
                            'stylesheets': list[str]()})
        self._opf_files.clear()
        self._load_container()

    def load_rendition(self, index: int = 0) -> None:
        index = min(index, len(self._opf_files) - 1)
        spine, stylesheets =\
            self._load_opf_file(self._opf_files[index])
        self._rendition = (index,
                           {'spine': spine,
                            'stylesheets': stylesheets})

    def get_rendition_paths(self)\
            -> tuple[list[str], list[str]]:
        opf_file_path, spine, stylesheets = self._get_rendition_data()
        opf_file_dirname = path.dirname(opf_file_path)
        spine_files_paths =\
            [paths_join_normalize(
                self.book_dir, opf_file_dirname, spine_file)
             for spine_file in spine]
        stylesheets_paths =\
            [paths_join_normalize(
                self.book_dir, opf_file_dirname, stylesheet)
             for stylesheet in stylesheets]
        return spine_files_paths, stylesheets_paths

    def get_opf_file_path(self):
        return self._get_rendition_data()[0]

    def get_opf_folder_path(self):
        return path.dirname(self.get_opf_file_path())

    # TODO: Replace with something sensible
    def get_font_folder_path(self, rendition_id: int = 0):
        return path.join(self.get_opf_folder_path(rendition_id), 'Fonts')

    def generate_manifest_id(self, base_name: str, rendition_id: int = 0):
        '''
        Generates a simple text with id based on given string
        by appending random numbers at the end untill there is no other that matches it
        '''

        # Copied from add_item_to_rendition_manifes. Probably would be better as a function
        content = self._read(self.renditions[rendition_id]['opf_file'])
        tree = self._parse_xml(content)
        manifest = tree.find(f'{{{NAMESPACES["OPF"]}}}manifest')
        children = manifest.getchildren()
        ids = []
        for child in children:
            ids.append(child.get('id'))

        if base_name not in ids:
            return base_name

        # Very simple id generation. Replace with something decent if need be
        base_name += '_'
        while base_name in ids:
            base_name = base_name + str(random.randrange(0, 9))

        return base_name


    def add_item_to_rendition_manifest(self,
                                       item_attributes: list[str, str, str],
                                       rendition_id: int = 0) -> None:
        '''
        Works if `item_attributes[0]` is unique id and `item_attributes[1]` refers to a file not added to manifest already 
        '''
        content = self._read(self.renditions[rendition_id]['opf_file'])
        tree = self._parse_xml(content)
        manifest = tree.find(f'{{{NAMESPACES["OPF"]}}}manifest')
        children = manifest.getchildren()
        ids, hrefs = [], []
        for child in children:
            ids.append(child.get('id'))
            hrefs.append(child.get('href'))
        opf_file_path = paths_join_normalize(
            self.book_dir, self.renditions[rendition_id]['opf_file'])
        opf_file_dirname = path.dirname(opf_file_path)
        item_attributes[1] = path.relpath(item_attributes[1], opf_file_dirname)
        if item_attributes[1] in hrefs:
            return  # file already added
        if item_attributes[0] in ids:
            pass  # change id
        item = manifest.makeelement(f'{{{NAMESPACES["OPF"]}}}item',
                                    attrib={'id': item_attributes[0],
                                            'href': item_attributes[1],
                                            'media-type': item_attributes[2]})
        item.tail = children[-1].tail
        children[-1].tail = manifest.text
        manifest.extend([item])
        serialized = etree.tostring(tree, encoding='utf-8', xml_declaration=True)
        with open(opf_file_path, 'wb') as file:
            file.write(serialized)

    def remove_item_from_rendition_manifest(self, item_id: str = None, item_path: str = None, rendition_id: int = 0) -> tuple[bool, bool]:
        '''
        Probably works\n
        Removes item with both id and href or at leas one of them matching given values(scenario dependand on given set of values)\n
        First bool from returned tuple is `True` if item was removed, second - if file itself can be removed because it is not mentioned in manifests of other renditions
        '''
        if item_id is None and item_path is None:
            return False, False
        content = self._read(self.renditions[rendition_id]['opf_file'])
        tree = self._parse_xml(content)
        manifest = tree.find(f'{{{NAMESPACES["OPF"]}}}manifest')
        children = manifest.getchildren()
        if len(children) <= 2:  # at least 1 item in manifest
            return False, False
        opf_file_path = paths_join_normalize(
            self.book_dir, self.renditions[rendition_id]['opf_file'])
        opf_file_dirname = path.dirname(opf_file_path)
        href = item_path
        if href is not None:
            href = path.relpath(href, opf_file_dirname)

        matches = []
        for child in children:
            child_id = child.get('id')
            child_href = child.get('href')
            if item_id is not None and href is not None:
                if item_id == child_id and href == child_href:
                    matches.append(child)
            elif item_id is not None:
                if item_id == child_id:
                    matches.append(child)
            elif href == child_href:
                matches.append(child)
            elif item_id in child_id:
                matches.append(child)
        if len(matches) != 1:
            return False, False
        match = matches[0]
        if match == children[-1]:
            children[-2].tail = children[-1].tail
        item_path = paths_join_normalize(opf_file_dirname, match.get('href'))
        manifest.remove(match)
        serialized = etree.tostring(tree, encoding='utf-8', xml_declaration=True)
        with open(opf_file_path, 'wb') as file:
            file.write(serialized)

        for i in range(len(self.renditions)):
            if i == rendition_id:
                continue
            rendition_rel_path = self.renditions[i]['opf_file']
            opf_file_dirname = path.dirname(paths_join_normalize(self.book_dir, rendition_rel_path))
            href = path.relpath(item_path, opf_file_dirname)
            content = self._read(rendition_rel_path)
            tree = self._parse_xml(content)
            manifest = tree.find(f'{{{NAMESPACES["OPF"]}}}manifest')
            children = manifest.getchildren()
            for child in children:
                if child.get('href') == href:
                    return True, False
        return True, True

    def get_rendition_manifest_items_attributes(self, rendition_id: int = 0) -> list[tuple[str, str, str]]:
        '''
        Works for sure
        '''
        content = self._read(self.renditions[rendition_id]['opf_file'])
        tree = self._parse_xml(content)
        manifest = tree.find(f'{{{NAMESPACES["OPF"]}}}manifest')
        children = manifest.getchildren()
        attributes = [(child.get('id'), child.get('href'), child.get('media-type')) for child in children]
        return attributes

    def _parse_xml(self, xml: str) -> None:
        try:
            tree = etree.parse(io.BytesIO(xml.encode('utf-8')))
        except etree.Error:
            tree = etree.parse(io.BytesIO(xml))

        return tree

    def _get_rendition_data(self) -> tuple[str, list[str], list[str]]:
        if self._rendition[0] == -1:
            raise RuntimeError('No rendition has been loaded yet, \
use load_rendition() method first')
        return self._opf_files[self._rendition[0]],\
            self._rendition[1]['spine'],\
            self._rendition[1]['stylesheets']

    def _load_container(self) -> None:
        try:
            meta_inf = self._read('META-INF/container.xml')
        except FileNotFoundError as e:
            raise FileNotFoundError('This ".epub" file does not \
contain the \"META-INF/container.xml\", which is required by the \
standard and therefore cannot be read') from e

        tree = self._parse_xml(meta_inf)

        views = tree.findall('//xmlns:rootfile[@media-type]',
                             namespaces={'xmlns': NAMESPACES['CONTAINERS']})
        if len(views) == 0:
            raise MissingValueError('\"META-INF/container.xml\" in this epub \
contains no referrence to file describing structure of the book view, \
and therefore book cannot be read')
        for root_file in views:
            if root_file.get('media-type') == 'application/oebps-package+xml':
                self._opf_files.append(root_file.get('full-path'))
        if len(self._opf_files) == 0:
            raise MissingValueError('None of book rendition references \
in \"META-INF/container.xml\" is marked with proper media-type and therefore, \
file is non-compliant with the standard')

    def _read(self, name: str) -> str:
        with open(path.join(self.book_dir, name), "r") as file:
            content = file.read()
        return content

    def _load_opf_file(self, opf_file_internal_path: str)\
            -> tuple[list[str], list[str]]:
        try:
            content = self._read(opf_file_internal_path)
        except FileNotFoundError:
            raise FileNotFoundError(-1, 'Can not find container file')

        container = self._parse_xml(content)

        #self._load_metadata()
        id_to_href, stylesheets = self._load_manifest(container)
        spine = self._load_spine(container, id_to_href)
        #self._load_guide()

        return spine, stylesheets

#    '''def _load_metadata(self):
#        container_root = self.container.getroot()
#
#        # get epub version
#        self.book.version = container_root.get('version', None)
#
#        # get unique-identifier
#        if container_root.get('unique-identifier', None):
#            self.book.IDENTIFIER_ID = container_root.get('unique-identifier')
#
#        # get xml:lang
#        # get metadata
#        metadata = self.container.find('{%s}%s' % (NAMESPACES['OPF'],
#                                       'metadata'))
#
#        nsmap = metadata.nsmap
#        nstags = dict((k, '{%s}' % v) for k, v in six.iteritems(nsmap))
#        default_ns = nstags.get(None, '')
#
#        nsdict = dict((v, {}) for v in nsmap.values())
#
#        def add_item(ns, tag, value, extra):
#            if ns not in nsdict:
#                nsdict[ns] = {}
#
#            values = nsdict[ns].setdefault(tag, [])
#            values.append((value, extra))
#
#        for t in metadata:
#            if not etree.iselement(t) or t.tag is etree.Comment:
#                continue
#            if t.tag == default_ns + 'meta':
#                name = t.get('name')
#                others = dict((k, v) for k, v in t.items())
#
#                if name and ':' in name:
#                    prefix, name = name.split(':', 1)
#                else:
#                    prefix = None
#
#                add_item(t.nsmap.get(prefix, prefix), name, t.text, others)
#            else:
#                tag = t.tag[t.tag.rfind('}') + 1:]
#
#                if t.prefix and t.prefix.lower() == 'dc'\
#                   and tag == 'identifier':
#                    _id = t.get('id', None)
#
#                    if _id:
#                        self.book.IDENTIFIER_ID = _id
#
#                others = dict((k, v) for k, v in t.items())
#                add_item(t.nsmap[t.prefix], tag, t.text, others)
#
#        self.book.metadata = nsdict
#
#        titles = self.book.get_metadata('DC', 'title')
#        if len(titles) > 0:
#            self.book.title = titles[0][0]
#
#        for value, others in self.book.get_metadata('DC', 'identifier'):
#            if others.get('id') == self.book.IDENTIFIER_ID:
#                self.book.uid = value'''

    def _load_manifest(self, container) -> tuple[dict[str, str], list[str]]:
        items = dict[str, str]()
        stylesheets = list[str]()
        assignments = {
            'text/css': lambda href: stylesheets.append(href),
        }
        for entry in container.find(f'{{{NAMESPACES["OPF"]}}}manifest'):
            if entry is not None and\
               entry.tag != f'{{{NAMESPACES["OPF"]}}}item':
                continue
            href = entry.get('href')
            items[entry.get('id')] = href
            try:
                assignments[entry.get('media-type')](href)
            except KeyError:
                pass
        return items, stylesheets

#            '''media_type = r.get('media-type')
#            _properties = r.get('properties', '')
#
#            if _properties:
#                properties = _properties.split(' ')
#            else:
#                properties = []
#
#            # people use wrong content types
#            if media_type == 'image/jpg':
#                media_type = 'image/jpeg'
#
#            if media_type == 'application/x-dtbncx+xml':
#                ei = EpubNcx(uid=r.get('id'), file_name=parse.unquote(r.get('href')))
#
#                ei.content = self.read_file(zip_path.join(self.opf_dir, ei.file_name))
#            if media_type == 'application/smil+xml':
#                ei = EpubSMIL(uid=r.get('id'), file_name=parse.unquote(r.get('href')))
#
#                ei.content = self.read_file(zip_path.join(self.opf_dir, ei.file_name))
#            elif media_type == 'application/xhtml+xml':
#                if 'nav' in properties:
#                    ei = EpubNav(uid=r.get('id'), file_name=parse.unquote(r.get('href')))
#
#                    ei.content = self.read_file(zip_path.join(self.opf_dir, r.get('href')))
#                elif 'cover' in properties:
#                    ei = EpubCoverHtml()
#
#                    ei.content = self.read_file(zip_path.join(self.opf_dir, parse.unquote(r.get('href'))))
#                else:
#                    ei = EpubHtml()
#
#                    ei.id = r.get('id')
#                    ei.file_name = parse.unquote(r.get('href'))
#                    ei.media_type = media_type
#                    ei.media_overlay = r.get('media-overlay', None)
#                    ei.media_duration = r.get('duration', None)
#                    ei.content = self.read_file(zip_path.join(self.opf_dir, ei.get_name()))
#                    ei.properties = properties
#            elif media_type in IMAGE_MEDIA_TYPES:
#                if 'cover-image' in properties:
#                    ei = EpubCover(uid=r.get('id'), file_name=parse.unquote(r.get('href')))
#
#                    ei.media_type = media_type
#                    ei.content = self.read_file(zip_path.join(self.opf_dir, ei.get_name()))
#                else:
#                    ei = EpubImage()
#
#                    ei.id = r.get('id')
#                    ei.file_name = parse.unquote(r.get('href'))
#                    ei.media_type = media_type
#                    ei.content = self.read_file(zip_path.join(self.opf_dir, ei.get_name()))
#            else:
#                # different types
#                ei = EpubItem()
#
#                ei.id = r.get('id')
#                ei.file_name = parse.unquote(r.get('href'))
#                ei.media_type = media_type
#
#                ei.content = self.read_file(zip_path.join(self.opf_dir, ei.get_name()))
#
#            self.book.add_item(ei)'''
#
#        # read nav file if found
#
#        '''nav_item = next((item for item in self.book.items if isinstance(item, EpubNav)), None)
#        if nav_item:
#            if not self.book.toc:
#                self._parse_nav(
#                    nav_item.content,
#                    path.dirname(nav_item.file_name),
#                    navtype='toc'
#                )
#            self._parse_nav(
#                nav_item.content,
#                path.dirname(nav_item.file_name),
#                navtype='pages'
#            )'''
#
#    '''def _parse_ncx(self, data):
#        tree = parse_string(data)
#        tree_root = tree.getroot()
#
#        nav_map = tree_root.find('{%s}navMap' % NAMESPACES['DAISY'])
#
#        def _get_children(elems, n, nid):
#            label, content = '', ''
#            children = []
#
#            for a in elems.getchildren():
#                if a.tag == '{%s}navLabel' % NAMESPACES['DAISY']:
#                    label = a.getchildren()[0].text
#                if a.tag == '{%s}content' % NAMESPACES['DAISY']:
#                    content = a.get('src', '')
#                if a.tag == '{%s}navPoint' % NAMESPACES['DAISY']:
#                    children.append(_get_children(a, n + 1, a.get('id', '')))
#
#            if len(children) > 0:
#                if n == 0:
#                    return children
#
#                return (Section(label, href=content),
#                        children)
#            else:
#                return Link(content, label, nid)
#
#        self.book.toc = _get_children(nav_map, 0, '')
#
#    def _parse_nav(self, data, base_path, navtype='toc'):
#        html_node = parse_html_string(data)
#        if navtype == 'toc':
#            # parsing the table of contents
#            nav_node = html_node.xpath("//nav[@*='toc']")[0]
#        else:
#            # parsing the list of pages
#            _page_list = html_node.xpath("//nav[@*='page-list']")
#            if len(_page_list) == 0:
#                return
#            nav_node = _page_list[0]
#
#        def parse_list(list_node):
#            items = []
#
#            for item_node in list_node.findall('li'):
#
#                sublist_node = item_node.find('ol')
#                link_node = item_node.find('a')
#
#                if sublist_node is not None:
#                    title = item_node[0].text
#                    children = parse_list(sublist_node)
#
#                    if link_node is not None:
#                        href = zip_path.normpath(zip_path.join(base_path, link_node.get('href')))
#                        items.append((Section(title, href=href), children))
#                    else:
#                        items.append((Section(title), children))
#                elif link_node is not None:
#                    title = link_node.text
#                    href = zip_path.normpath(zip_path.join(base_path, link_node.get('href')))
#
#                    items.append(Link(href, title))
#
#            return items
#
#        if navtype == 'toc':
#            self.book.toc = parse_list(nav_node.find('ol'))
#        elif nav_node is not None:
#            # generate the pages list if there is one
#            self.book.pages = parse_list(nav_node.find('ol'))
#
#            # generate the per-file pages lists
#            # because of the order of parsing the files, this can't be done
#            # when building the EpubHtml objects
#            htmlfiles = dict()
#            for htmlfile in self.book.items:
#                if isinstance(htmlfile, EpubHtml):
#                    htmlfiles[htmlfile.file_name] = htmlfile
#            for page in self.book.pages:
#                try:
#                    (filename, idref) = page.href.split('#')
#                except ValueError:
#                    filename = page.href
#                if filename in htmlfiles:
#                    htmlfiles[filename].pages.append(page)'''

    def _load_spine(self, container, id_to_href: dict[str, str]) -> list[str]:
        spine = container.find(f'{{{NAMESPACES["OPF"]}}}spine')

        '''
        From: https://www.w3.org/publishing/epub3/epub-packages.html#attrdef-itemref-linear
        The linear attribute indicates whether the referenced item contains
        content that contributes to the primary reading order and has to be
        read sequentially ("yes") or auxiliary content that enhances or
        augments the primary content and can be accessed
        out of sequence ("no").
        Examples of auxiliary content include: notes, descriptions and
        answer keys.
        '''
        content = [[], []]  # value of linear 'yes' and 'no'
        for entry in spine:
            id_ref = entry.get('idref')
            index = 0
            if entry.get('linear', 'yes') != 'yes':
                index = 1
            content[index].append(id_ref)
        for i in range(len(content)):
            for j in range(len(content[i])):
                content[i][j] = id_to_href[content[i][j]]
        return content[0] + content[1]

#        '''toc = spine.get('toc', '')
#        direction = spine.get('page-progression-direction', None)'''
#
#        # should read ncx or nav file
#        '''if toc:
#            try:
#                ncxFile = self.read_file(path.join(self.opf_dir, self.book.get_item_with_id(toc).get_name()))
#            except KeyError:
#                raise FileNotFoundError(-1, 'Can not find ncx file.')
#
#            self._parse_ncx(ncxFile)'''
#
#    '''def _load_guide(self):
#        guide = self.container.find('{%s}%s' % (NAMESPACES['OPF'], 'guide'))
#        if guide is not None:
#            self._guide = [{'href': t.get('href'), 'title': t.get('title'),
#                            'type': t.get('type')} for t in guide]'''
#