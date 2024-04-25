import xml.etree.ElementTree as et
import sys
import getopt
import os.path


class Label:
    def __init__(self, name, number):
        self.name = name
        self.number = number


class StackData:
    def __init__(self, type, value):
        self.type = type
        self.value = value


class Stack:
    def __init__(self):
        self.stack = []

    def stack_push(self, data):
        self.stack.append(data)

    def stack_pop(self):
        if len(self.stack) == 0:
            exit(56)
        return self.stack.pop()
    

class Arg:
    def __init__(self, arg_type, value):
        self.arg_type = arg_type
        self.value = value


class Instruction:
    def __init__(self, name, number):
        self.name = name
        self.number = number
        self.args = []

    def add_arg(self, arg):
        self.args.append(arg)


class FrameRecord:
    def __init__(self, name, type, value):
        self.type = type
        self.value = value
        self.name = name


class Frame:
    def __init__(self):
        self.frame_records = []

    def insert_record(self, record):
        self.frame_records.append(record)

    def search_record(self, search, defvar=False):
        found = False
        for record in self.frame_records:
            if record.name == search.value:
                if defvar:
                    print('Opakovana definice promenne!', file=sys.stderr)
                    exit(52)
                found = True
                break

        if found:
            return record
        else:
            if not defvar:
                print('Prace s neexistujici promennou!', file=sys.stderr)
                exit(54)
            return None
        
    def modify_record(self, record, name, type, value):
            record.type = type
            record.value = value
            record.name = name
    

instructions = []
lokal_frames = []
call_stack = []
labels = []
temp_frame = None
global_frame = Frame()
stack = Stack()
index = 1
input_file = ''
source_file = ''

# Zkontroluje zda dany soubor existuje, jinak `exit 11`
def file_existence(file):
    if file != '':
        if not os.path.isfile(file):
            print('Soubor: `', file, '` neexistuje!', file=sys.stderr)
            exit(11)

# Podle nazvu promenne vybere urcity ramec, do ktereho se ma hodnota ulozit
# a ten pak vrati
def select_frame(arg):
    if arg.value[:2] == 'GF':
        return global_frame
    elif arg.value[:2] == 'LF':
        if len(lokal_frames) == 0:
            print('Pristup k neexistujicimu framu!', file=sys.stderr)
            exit(55)
        return lokal_frames[-1]
    elif arg.value[:2] == 'TF':
        if temp_frame is None:
            print('Pristup k neexistujicimu framu!', file=sys.stderr)
            exit(55)
        return temp_frame
    else:
        print('Spatne pojmenovani promenne!', file=sys.stderr)
        exit(52)

# Nahradi jeden znak na urcite pozici a vrati upraveny string
def replace(string, pos, replace):
    var = list(string)
    var[int(pos)] = replace
    return "".join(var) 

# Nahradi urcite kombina cisel jejimi reprezentacemi pomoci dict a funkce replace
def modify_string(string):
    nahrad = {
        '\\000': '\x00', '\\001': '\x01', '\\002': '\x02', '\\003': '\x03', '\\004': '\x04',
        '\\005': '\x05', '\\006': '\x06', '\\007': '\x07', '\\008': '\x08', '\\009': '\x09',
        '\\010': '\x0A', '\\011': '\x0B', '\\012': '\x0C', '\\013': '\x0D', '\\014': '\x0E',
        '\\015': '\x0F', '\\016': '\x10', '\\017': '\x11', '\\018': '\x12', '\\019': '\x13',
        '\\020': '\x14', '\\021': '\x15', '\\022': '\x16', '\\023': '\x17', '\\024': '\x18',
        '\\025': '\x19', '\\026': '\x1A', '\\027': '\x1B', '\\028': '\x1C', '\\029': '\x1D',
        '\\030': '\x1E', '\\031': '\x1F', '\\032': '\x20', '\\035': '\x23', '\\092': '\x5c',
    }

    for key, value in nahrad.items():
        string = string.replace(key, value)

    return string

# Provede urcitiou aritmetickou operaci. 
def artitmetic(op, args):
    if args[1].arg_type == 'var':
        selected_frame = select_frame(args[1])
        record = selected_frame.search_record(args[1])
        if not record.value.isnumeric():
            print('Spatny typ pri aritmeticke operaci!', file=sys.stderr)
            exit(53)
        a = int(record.value)
    elif args[1].arg_type == 'int':
        a = int(args[1].value)
    else:
        print('Nespravny typ pri aritmetickych operaci!', file=sys.stderr)
        exit(53)
        
    if args[2].arg_type == 'var':
        selected_frame = select_frame(args[2])
        record = selected_frame.search_record(args[2])
        if not record.value.isnumeric():
            print('Spatny typ pri aritmeticke operaci!', file=sys.stderr)
            exit(53)
        b = int(record.value)
    elif args[2].arg_type == 'int':
        b = int(args[2].value)
    else:
        print('Nespravny typ pri aritmetickych operaci!', file=sys.stderr)
        exit(53)
       
    if op == 'ADD':
        return a + b
    elif op == 'SUB':
        return a - b
    elif op == 'MUL':
        return a * b
    if op == 'IDIV':
        if b == 0:
            exit(57)
        return a // b

# Zjisti typ a vraci typ i hodnotu
def get_type(type, value):
    var_type = type
    if type == 'nil':
        var = 'nil'
    elif type == 'string':
        var = value
    elif type == 'int':
        var = int(value)
    elif type == 'bool':
        if value == 'false':
            var = False
        else:
            var = True
    return var_type, var

# Prevadi hodnotu na True na true a False na false
# Pro pristum k ramci, nejdriv pomoci `select_frame()` se vybere spravny ramec
# a pote moci `search_record()` nalezne dana promena.
# Pomoci `modify_record()` se ramec auktualizuje
def modify_bool(var):
    if var:
        return 'true'
    else:
        return 'false'

# Rozhoduje se o jakou instrukci se jedna a provede ji
def do_instruction(ins_name, args):
    global temp_frame, index

    if ins_name == 'MOVE': 
        var = args[1].value 
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            var = record.value 
        
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, args[1].arg_type, var)

    elif ins_name == 'CREATEFRAME':
        temp_frame = Frame()

    elif ins_name == 'PUSHFRAME':
        if temp_frame == None:
            print('Pristup k neexistujicimu framu!', file=sys.stderr)
            exit(55)

        for record in temp_frame.frame_records:
            record.name = replace(record.name, 0, 'L')

        lokal_frames.append(temp_frame)
        temp_frame = None

    elif ins_name == 'POPFRAME':
        if len(lokal_frames) == 0:
            print('Pristup k neexistujicimu framu!', file=sys.stderr)
            exit(55)

        for record in lokal_frames[-1].frame_records:
            record.name = replace(record.name, 0, 'T')

        temp_frame = lokal_frames.pop()   

    elif ins_name == 'DEFVAR':
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0], defvar=True)
        selected_frame.insert_record(FrameRecord(args[0].value, None, None))

    elif ins_name == 'CALL':
        call_stack.append(index)
        found = False
        for label in labels:
            if label.name == args[0].value:
                found = True
                index = int(label.number) - 2
                break
        if not found:
            print("Label nenalezen!", file=sys.stderr)
            exit(52)

    elif ins_name == 'RETURN':                
        if len(call_stack) == 0:
            print("Pokus o ziskani hodnoty v prazdne zasobniku!", file=sys.stderr)
            exit(56)
        index = call_stack.pop()       

    elif ins_name == 'PUSHS':
        if args[0].arg_type == 'var':
            selected_frame = select_frame(args[0])
            record = selected_frame.search_record(args[0])

            data = StackData(record.type, record.value)
        else:
            data = StackData(args[0].arg_type, args[0].value)

        stack.stack_push(data)

    elif ins_name == 'POPS':
        data = stack.stack_pop()
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, data.type, data.value)

    elif (ins_name == 'ADD'
        or ins_name == 'SUB'
        or ins_name == 'MUL'
        or ins_name == 'IDIV'):
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'int', artitmetic(ins_name, args))

    elif (ins_name == 'LT'
        or ins_name == 'GT'
        or ins_name == 'EQ'):
        a = args[1].value 
        type_a = args[1].arg_type

        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            type_a, a = get_type(record.type, record.value)
        else:
            type_a, a = get_type(args[1].arg_type, args[1].value)

        b = args[2].value 
        type_b = args[2].arg_type
        if args[2].arg_type == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            type_b, b = get_type(record.type, record.value)
        else:
            type_b, b = get_type(args[2].arg_type, args[2].value)

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0]) 

        if type_b == 'var' or type_a == 'var':
            print("Neplatna kombinace typu!", file=sys.stderr)
            exit(53)

        if ins_name == 'LT':
            if type_a != type_b or type_a == 'nil' or type_b == 'nil':
                print("Neplatna kombinace typu!", file=sys.stderr)
                exit(53)  
            var = a < b
        elif ins_name == 'GT':
            if type_a != type_b or type_a == 'nil' or type_b == 'nil':
                print("Neplatna kombinace typu!", file=sys.stderr)
                exit(53)  
            var = a > b
        else:
            if type_b != 'nil' and type_a != 'nil':
                if type_a != type_b:
                    print("Neplatna kombinace typu!", file=sys.stderr)
                    exit(53)                
            var = a == b
        
        if var:
            var = 'true'
        else:
            var = 'false'
        selected_frame.modify_record(record, record.name, 'bool', var)

    elif (ins_name == 'AND'
        or ins_name == 'OR'
        or ins_name == 'NOT'):
        var = args[1].value 
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'bool':
                print("Typ musi byt bool!", file=sys.stderr)
                exit(53)
            a = record.value 
        elif args[1].arg_type == 'bool':
            a = args[1].value
        else:
            print("Typ musi byt bool!", file=sys.stderr)
            exit(53)

        if ins_name != 'NOT':
            if args[2].arg_type == 'var':
                selected_frame = select_frame(args[2])
                record = selected_frame.search_record(args[2])
                if record.type != 'bool':
                    print("Typ musi byt bool!", file=sys.stderr)
                    exit(53)
                b = record.value 
            elif args[2].arg_type == 'bool':
                b = args[2].value
            else:
                print("Typ musi byt bool!", file=sys.stderr)
                exit(53)

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])     
        if ins_name == 'AND':
            var = a == 'true' and b == 'true'
            var = modify_bool(var)
        elif ins_name == 'OR':
            var = a == 'true' or b == 'true'
            var = modify_bool(var)
        else:
            var = a != 'true'
            var = modify_bool(var)

        selected_frame.modify_record(record, record.name, 'bool', var)
    
    elif ins_name == 'INT2CHAR':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type == 'int':
                var = chr(int(record.value))
            else:
                print("Typ musi byt int!", file=sys.stderr)
                exit(53)

        elif args[1].arg_type == 'int':
            if int(args[1].value) >= 0 and int(args[1].value) <= 127:
                var = chr(int(args[1].value))
            else:
                print("Neplatny rozsah cisla. Pouze od 0 do 127!", file=sys.stderr)
                exit(58)
        else:
            print("Typ musi byt int!", file=sys.stderr)
            exit(53)

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'string', var)

    elif ins_name == 'STRI2INT':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'string':
                print("Typ musi byt stirng!", file=sys.stderr)
                exit(53)
            var = record.value
        elif args[1].arg_type == 'string':
            var = args[1].value
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        if args[2].arg_type == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            if record.type != 'int':
                print("Typ musi byt int!", file=sys.stderr)
                exit(53)
            x = record.value
        elif args[2].arg_type == 'int':
            x = args[2].value
        else:
            print("Typ musi byt int!", file=sys.stderr)
            exit(53)
        if len(var) <= int(x):
            print("Cislo je mimo rozsah stringu!", file=sys.stderr)
            exit(58)

        var = list(var)
        var = ord(var[int(x)])

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'int', var)
    
    elif ins_name == 'READ':
        var = args[0].value
        var_type = args[1].value
        if var_type not in { 'int', 'string', 'bool', 'nil' }:
            print("Neplatny typ!", file=sys.stderr)
            exit(32)
        input_val = ''
        if input_file != '':
            file_existence(input_file)
            with open(input_file, 'r') as f:
                input_val = f.read().strip()
            if len(input_val) == 0:
                var_type = 'nil'
        else:
            input_val = input()
            if len(input_val) == 0:
                var_type = 'nil'

        if var_type == 'int':
            if input_val.isnumeric():

                var_val = int(input_val)
            else:
                var_type = 'nil'
                var_val = 'nil'
        elif var_type == 'string':
            var_val = str(input_val)
        elif var_type == 'bool':
            if input_val.lower() == 'true':
                var_val = input_val
            else:
                var_val = 'false'              
        else:
            var_val = None

        if var_val is None:
            var_val = 'nil'
            var_type = 'nil'

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, var, var_type, var_val)
   
    elif ins_name == 'WRITE':
        if args[0].arg_type == 'var':
            selected_frame = select_frame(args[0])
            record = selected_frame.search_record(args[0])
            var = str(record.value)
            var_type = record.type
        else:
            var = str(args[0].value)
            var_type = args[0].arg_type
        if var_type == 'nil':
            print('', end='')
        else:
            var = var.strip()
            print(modify_string(var), end='')
    
    elif ins_name == 'CONCAT':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'string':
                print("Typ musi byt string!", file=sys.stderr)
                exit(53)
            stri1 = record.value
        elif args[1].arg_type == 'string':
            stri1 = args[1].value
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        if args[2].arg_type == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            if record.type != 'string':
                print("Typ musi byt string!", file=sys.stderr)
                exit(53)
            stri2 = record.value
        elif args[2].arg_type == 'string':
            stri2 = args[2].value
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        var = stri1 + stri2
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'string', var)

    elif ins_name == 'STRLEN':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'string':
                print("Typ musi byt string!", file=sys.stderr)
                exit(53)
            stri = record.value
        elif args[1].arg_type == 'string':
            stri = args[1].value
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'int', len(stri))

    elif ins_name == 'GETCHAR':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'string':
                print("Typ musi byt string!", file=sys.stderr)
                exit(53)
            stri = record.value
        elif args[1].arg_type == 'string':
            stri = args[1].value
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        if args[2].arg_type == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            if record.type != 'int':
                print("Typ musi byt int!", file=sys.stderr)
                exit(53)
            x = int(record.value)
        elif args[2].arg_type == 'int':
            x = int(args[2].value)
        else:
            print("Typ musi byt int!", file=sys.stderr)
            exit(53)

        if x >= len(stri):
            print("Cislo je mimo rozsah stringu!", file=sys.stderr)
            exit(58)
            
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, args[1].arg_type, stri[x])

    elif ins_name == 'SETCHAR':
        if args[2].arg_type == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            if record.type != 'string':
                print("Typ musi byt string!", file=sys.stderr)
                exit(53)
            if record.value is None:
                print("Prazdny retezec!", file=sys.stderr)
                exit(58)
            stri = record.value
        elif args[2].arg_type == 'string':
            stri = args[2].value
            if len(stri) == 0:
                print("Delka je velikosti 0!", file=sys.stderr)
                exit(58)
        else:
            print("Typ musi byt string!", file=sys.stderr)
            exit(53)

        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            if record.type != 'int':
                print("Typ musi byt int!", file=sys.stderr)
                exit(53)
            x = int(record.value)
        elif args[1].arg_type == 'int':
            x = int(args[1].value)
        else:
            print("Typ musi byt int!", file=sys.stderr)
            exit(53)

        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])

        if x >= len(record.value):
            print("Cislo je mimo rozsah stringu!", file=sys.stderr)
            exit(58)
        var = replace(record.value, x, stri)
        selected_frame.modify_record(record, record.name, 'string',var)
    
    elif ins_name == 'TYPE':
        if args[1].arg_type == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            symb_type = record.type
        else:
            symb_type = args[1].arg_type
        if symb_type is None:
            symb_type = ''
        selected_frame = select_frame(args[0])
        record = selected_frame.search_record(args[0])
        selected_frame.modify_record(record, record.name, 'string', symb_type)

    elif ins_name == 'JUMP':
        found = False
        for label in labels:
            if label.name == args[0].value:
                found = True
                index = int(label.number) - 2
                break
        if not found:
            print("Label neexistuje!", file=sys.stderr)
            exit(52)
    
    elif ins_name == 'JUMPIFEQ':
        typea = args[1].arg_type
        typeb = args[2].arg_type
        a = args[1].value
        b = args[2].value
        if typea == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            typea = record.type
            a = record.value

        if typeb == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            typeb = record.type
            b = record.value
        if typea != typeb:
            if typea != 'nil' or typeb != 'nil':
                print("Neplatny typ!", file=sys.stderr)
                exit(53)
        found = False
        if a == b:
            for label in labels:
                if label.name == args[0].value:
                    found = True
                    index = int(label.number) - 2
            if not found:
                print("Label neexistuje!", file=sys.stderr)
                exit(52)
    elif ins_name == 'JUMPIFNEQ':
        typea = args[1].arg_type
        typeb = args[2].arg_type
        a = args[1].value
        b = args[2].value
        if typea == 'var':
            selected_frame = select_frame(args[1])
            record = selected_frame.search_record(args[1])
            typea = record.type
            a = record.value

        if typeb == 'var':
            selected_frame = select_frame(args[2])
            record = selected_frame.search_record(args[2])
            typeb = record.type
            b = record.value
        if typea != typeb:
            if typea != 'nil' or typeb != 'nil':
                print("Neplatny typ!", file=sys.stderr)
                exit(53)
        found = False
        if a != b:
            for label in labels:
                if label.name == args[0].value:
                    index = int(label.number) - 2
                    found = True
            if not found:
                print("Label nebeexistuje!", file=sys.stderr)
                exit(52)

    elif ins_name == 'EXIT':
        var = args[0].value
        type_var = args[0].arg_type
        if args[0].arg_type == 'var':
            selected_frame = select_frame(args[0])
            record = selected_frame.search_record(args[0])
            type_var = record.type
            var = record.value

        if type_var != 'int':
            print("Typ musi byt int!", file=sys.stderr)
            exit(53)
        if int(var) < 0 or int(var) > 49:
            print("Neplatne rozmezi! Pouze mezi 0 az 49!", file=sys.stderr)
            exit(57)
        exit(int(var))

    elif ins_name == 'DPRINT':
        print(args[0].value, file=sys.stderr)
   
# funkce main pomoci getopt projde argumenty a zkontroluje je
def main(argv):
    global index,input_file, source_file
    help = False   

    # Zkontroluje argumenty
    try:
        opts, args = getopt.getopt(argv, 'h', ['help', 'source=', 'input='])
    except getopt.GetoptError:
        print('Neznama kombinace argumentu!', file=sys.stderr)
        exit(10)
 
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help = True
        elif opt == "--source":
            source_file = arg
        elif opt == "--input":
            input_file = arg

    if help:
        if source_file != '' or input_file != '':
            print('Nepovolena kombinace argumentu', file=sys.stderr)
            exit(10)
        print('HELP: python3.10 interpret.py --source=<sourcefile> --input=<inputfile>')
        exit(0)

    if source_file == '' and input_file == '':
        print('Musi byt zadan aspon bud `source` nebo `input`!', file=sys.stderr)
        sys.exit(10)
    
    if source_file == '':
        source_file = input()
    
    file_existence(source_file)

    # Ulozi obsah source do `tree`
    tree = et.parse(source_file)
    root = tree.getroot()

    if root.tag != 'program':
        print('XML soubor nezacina s `program`!', file=sys.stderr)
        exit(32)
    if root.attrib.get('language') != 'IPPcode23':
        print("Nevalidni XML IPPcode23:", file=sys.stderr)
        exit(32)
    
    ins_order_check = 0
    # kazda iterace by mela byt `instrukce`
    # pote se zkontroluje jeji potomci a ulozi do listu s hodnoty `Instruction`
    for child in root:
        if child.tag != 'instruction':
            print("Nevalidni XML tag:",  file=sys.stderr)
            exit(32)
            
        opcode = child.attrib['opcode'].upper()
        if child.attrib['order'].strip().isnumeric():
            ins_order = int(child.attrib['order'].strip())
        else:
            print("Nevalidni XML order:", file=sys.stderr)
            exit(32)
        if ins_order <= ins_order_check:
            print("Nevalidni XML order:", file=sys.stderr)
            exit(32)
        order = index + 1
        index += 1
        ins = Instruction(opcode, order)
        arg_value = ''
        arg_num = 0
        sorted_args = sorted(child, key=lambda x: x.tag)
        for arg in sorted_args:
            check_num = arg.tag[-1]
            if check_num.isnumeric():
                if int(check_num) <= arg_num:
                    print("Nevalidni XML argument:", file=sys.stderr)
                    exit(32)
            else:
                print("Nevalidni XML argument:", file=sys.stderr)
                exit(32)
            arg_num += 1
            arg_type = arg.get('type')
            if arg_type is None:
                print("Nevalidni XML argument:", file=sys.stderr)
                exit(32)
            arg_value = arg.text
            if arg_value is not None:
                arg_value = str(arg_value).strip()
            arg = Arg(arg_type, arg_value)
            ins.add_arg(arg)
        ins_order_check += 1    
        instructions.append(ins)

    # ukladani pozice navjesti do listu labels s hodnoty `Label`
    for ins in instructions:
        if ins.name == "LABEL":
            for label in labels:
                if ins.args[0].value == label.name:
                    print("Navesti se stejnym jmenem existuje!", file=sys.stderr)
                    exit(52)
            labels.append(Label(ins.args[0].value, ins.number))

    index = 0
    # provedeni instrukci na pozici `index`
    while index < len(instructions):
        do_instruction(instructions[index].name, instructions[index].args)
        index += 1

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])