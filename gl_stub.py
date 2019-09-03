import requests
import pathlib
import shutil
from typing import Dict, Tuple, List, Optional
import xml.etree.ElementTree as ET
HERE = pathlib.Path(__file__).absolute().parent
GL_XML_URL = 'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/master/xml/gl.xml'  # noqa: E501


class Command:
    def __init__(self, e: ET.Element):
        '''
<command>
    <proto>void <name>glAccum</name></proto>
    <param group="AccumOp"><ptype>GLenum</ptype> <name>op</name></param>
    <param group="CoordF"><ptype>GLfloat</ptype> <name>value</name></param>
    <glx type="render" opcode="137"/>
</command>
        '''
        self.name = ''
        name = e.find('proto/name')
        if name is not None and name.text:
            self.name = name.text

    def __str__(self):
        return f'def {self.name}(): ...'


class Definition:
    def __init__(self, root: ET.Element):
        self.types: Dict[str, str] = {}
        for t in root.findall('types/type'):
            self.process_type(t)

        self.enums: Dict[str, List[Tuple[str, int]]] = {}
        for group in root.findall('enums'):
            self.process_enum(group)

        self.commands: Dict[str, Command] = {}
        for command in root.findall('commands/command'):
            self.process_command(command)

    def process_type(self, e: ET.Element):
        name: Optional[ET.Element] = e.find('name')
        if name is not None:
            if name.text and e.text:
                self.types[name.text] = e.text

    def process_enum(self, e: ET.Element):
        def get_enum(kv: ET.Element) -> Optional[Tuple[str, int]]:
            name = kv.get('name')
            if name:
                value = kv.get('value')
                if value:
                    return (name, int(value, 16))
            return None

        values = [get_enum(e) for e in list(e)]
        g = e.get('group')
        if g:
            self.enums[g] = [v for v in values if v]

    def process_command(self, e: ET.Element):
        command = Command(e)
        self.commands[command.name] = command

    def process_feature(self, f, e: ET.Element):
        for x in list(e):
            name = x.get('name')
            if name:
                if x.tag == 'enum':
                    for k, v in self.enums.items():
                        for y in v:
                            if y[0] == name:
                                f.write(f'{y[0]} = {y[1]}\n')
                elif x.tag == 'command':
                    command = self.commands[name]
                    f.write(f'{command}\n')
                elif x.tag == 'type':
                    t = self.types[name]
                    f.write(f'# {name} = {t}\n')
                else:
                    raise Exception(f'unknown tag: {x.tag}')

    def generate(self, dst: pathlib.Path, root: ET.Element):
        dst.mkdir(parents=True, exist_ok=True)

        def get_pyi(api, major, minor):
            return f'{api.upper()}_{major}_{minor}.pyi'

        for e in root.findall('feature'):
            name = e.get("name")
            api = e.get("api")
            number = e.get("number")
            r = e.find('require')
            if name and api == 'gl' and number and r:
                print(f'{name} {api} {number}')
                with (dst / get_pyi(api, *number.split('.'))).open('w') as f:
                    self.process_feature(f, r)


def main() -> None:
    '''
    OpenGL
     + GL
        + VERSION
            + GL_1_0.pyi
    '''

    xml_file: pathlib.Path = (HERE / 'gl.xml')
    if not xml_file.exists():
        print(f'download: {GL_XML_URL}')
        r = requests.get(GL_XML_URL)
        with xml_file.open('w') as f:
            f.write(r.text)
            f.write('\n')

    root = ET.fromstring(xml_file.read_text())
    definition = Definition(root)

    dst: pathlib.Path = (HERE / 'out/OpenGL')
    if dst.exists():
        shutil.rmtree(dst)

    definition.generate(dst / 'VERSION', root)


if __name__ == '__main__':
    main()
