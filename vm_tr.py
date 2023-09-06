"""
This script acts as a translator of code from the VM (virtual machine) type to the ASM (Assembly) type.
The output can be directly loaded into the HACK computer and executed.
"""
import os


class Translator:
    '''
    The main class responsible for translation.
    Its instances contain lines of code being translated.
    Holds some important entities that are accessible to any instance.
    '''
    # generic patterns of code for each type of operation
    _code_patterns = dict()
    # mapping between operations and translating functions
    _func_mappings = dict()
    # storing the current state of translated .asm code
    _asm_code = ''
    # counting labeling operations
    _lt_eq_gt_counter = {'lt':0, 'eq':0, 'gt':0}

    def __init__(self, line_lst, class_name='', idx=0):
        self._line = line_lst
        self._class_name = class_name
        self._cmd = line_lst[0]
        self._idx = idx
        # substitute strings for (_pop) and (_push)
        self._pop_push_expr = ''

    @classmethod
    def create_mappings(cls, dir_path):
        '''
        Reads pattern files and adds pattern 
        names and their contents as entries 
        to the pattern dictionary.
        Maps each command to the appropriate
        function in the function dictionary.
        '''
        for filename in os.listdir(dir_path):
            if filename.endswith('.txt'):
                with open(os.path.join(dir_path, filename), 'r', encoding='utf-8') as file:
                    # removing comments/empty lines from the input
                    pattern_code = ''
                    for line in file:
                        if line[0] not in ('/', '\n', ' '):
                            pattern_code += line.replace(" ", "")
                    # creating {pattern name ---> pattern code} mapping
                    pattern_name = os.path.splitext(filename)[0]
                    cls._code_patterns[pattern_name] = pattern_code
                    # creating {command ---> function} mapping
                    if any(cmd in pattern_name for cmd in ('pop', 'push')):
                        func_name = '_pop_push'
                        cmd_lst = [pattern_name.split()[0][1:]]
                    elif any(cmd in pattern_name for cmd in ('label', 'goto', 'if-goto')):
                        func_name = '_label_goto_if_goto'
                        cmd_lst = [pattern_name[1:]]
                    else:
                        func_name = pattern_name
                        cmd_lst = [cmd for cmd in pattern_name.split('_') if cmd]

                    # linking all the detected commands to their function
                    for command in cmd_lst:
                        cls._func_mappings[command] = getattr(cls, func_name)
    
    @classmethod
    def get_output(cls):
        return Translator._asm_code 

    @classmethod
    def report_state(cls):
        output = 'CODE PATTERNS:' + '\n'
        for pattern_name, pattern_code in cls._code_patterns.items():
            output += 'pattern: ' + pattern_name + '\n'
            for line in pattern_code.splitlines():
                output += line + '\n'
            output += '\n'
        output += '\n'

        output += 'FUNCTION MAPPING:' + '\n'
        for cmd, function in cls._func_mappings.items():
            output += 'command: ' + cmd + '\n'
            output += 'function: ' + function.__name__ + '\n'
            output += '\n'

        return output
    
    def translate(self):
        '''
        Pre-processes the input (list of strings)
        Calls an appropriate translating function
        '''      
        # creating a comment
        if self._cmd != 'label':
            self._make_comm()
        # determine the right function for the current command
        op_func = Translator._func_mappings[self._cmd]
        func_name = op_func.__name__
        # getting corresponding pattern name
        if self._cmd in ('pop', 'push'):
            pattern_name = f'_{self._cmd}' + f' {self._line[1]}' if self._line[1] not in ('local', 'argument', 'this', 'that') \
                      else f'_{self._cmd}' + ' loc'
            
        elif self._cmd in ('label', 'goto', 'if-goto'):
            pattern_name = f'_{self._cmd}'

        else:
            pattern_name = func_name

        # getting specific strings for pop and push operations
        self._pop_push_helper() if self._cmd in ('pop', 'push') else None
        # loading code from the pattern
        raw_code = Translator._code_patterns[pattern_name]
        # getting translation from the function
        asm_code = op_func(self, raw_code)
        # updatng output
        Translator._asm_code += asm_code

    def _make_comm(self):
        '''
        Creates a comment specifying an operation
        '''
        comm_str = ' '.join(self._line)
        comm_str = '// ' + comm_str + '\n'
        # add the comment to the output string
        Translator._asm_code += comm_str

    def _pop_push_helper(self):
        mem_segm = self._line[1]
        i = self._line[2]
        loc_dict = {'local':1, 'argument':2, 'this':3, 'that':4}

        # for expressions of type pop/push pointer/loc -1/-2/-3...
        pointer_dict = {True:'-', False:'+'}
        # determine whether the <i> is negative
        try:
            is_neg = int(i) < 0
        except ValueError:
            is_neg = False
        # convert <i> to a positive value
        if is_neg:
            i = i[1:]

        static_expr = (self._class_name, i, None)
        temp_expr = (i, None, None)
        pointer_expr = (i, pointer_dict[is_neg], None)
        loc_expr = (str(loc_dict.get(mem_segm)), i, pointer_dict[is_neg])
        const_expr = (i, None, None)

        op_dict = {'static':static_expr, 'temp':temp_expr, 'pointer':pointer_expr,
                   'local':loc_expr, 'argument':loc_expr, 'this':loc_expr, 
                   'that':loc_expr, 'constant':const_expr}

        self._pop_push_expr = op_dict[mem_segm]

    def _pop_push(self, raw_code):
        '''
        Processes the 'POP' and 'PUSH' operations
        '''
        # substitute placeholders for the corresponding strings
        variables = {'var_1': self._pop_push_expr[0], 
                     'var_2': self._pop_push_expr[1],
                     'var_3': self._pop_push_expr[2]}
        formatted_code = raw_code.format(**variables)
        
        return formatted_code + '\n'
    
    def _add_sub_or_and(self, raw_code):
        '''
        Processes the following operations:
        'ADD', 'SUB', 'OR', 'AND'
        '''
        op_dict = {'add':'+', 'sub':'-', 'or':'|', 'and':'&'}
        # substitute placeholders for the corresponding strings
        formatted_code = raw_code.format(var_1 = op_dict[self._cmd])

        return formatted_code + '\n'

    def _neg_not(self, raw_code):
        '''
        Processes the following operations:
        'NEG', 'NOT'
        '''
        op_dict = {'neg':'-', 'not':'!'}
        # substitute placeholders for the corresponding strings
        formatted_code = raw_code.format(var_1 = op_dict[self._cmd])

        return formatted_code + '\n'

    def _lt_eq_gt(self, raw_code):
        '''
        Processes the following operations:
        'LT', 'EQ', 'GT'
        '''
        op_dict = {'lt': 'JGT', 'eq': 'JEQ', 'gt': 'JLT'}

        # increment the global counter
        Translator._lt_eq_gt_counter[self._cmd] += 1

        # substitute placeholders for the corresponding strings
        formatted_code = raw_code.format(var_1 = self._cmd.upper(), 
                                         var_2 = op_dict[self._cmd], 
                                         var_3 = Translator._lt_eq_gt_counter[self._cmd] - 1)
        
        return formatted_code + '\n'

    def _label_goto_if_goto(self, raw_code):
        '''
        Processes the 'LABEL', 'GOTO', 'IF-GOTO' operations
        '''
        lbl_name = self._line[1]
        # substitute placeholders for the corresponding strings
        formatted_code = raw_code.format(var_1 = lbl_name)

        return formatted_code + '\n'

    def _function(self, *args):
        '''
        Processes the FUNCTION command
        Inserts the label with the function name
        Pushes 0s as placeholders for local variables
        '''
        i = int(self._line[2])
        func_name = self._line[1]
        # creating a temporary list
        cmd_lst = []

        # inserting label declaration of the function
        cmd_lst.append(['label', f'{func_name}'])
        # inserting placeholders for local variables
        for _ in range(i):
            cmd_lst.append(['push', 'constant', '0'])
        # translating the resulting list of VM commands
        for line in cmd_lst:
            line_translator = Translator(line_lst=line)
            line_translator.translate()
        
        return ''

    def _call(self, *args):
        '''
        Processes the CALL command.
        Saves the frame of the current function
        onto the stack.
        Jumps to the function being called.
        '''
        func_name = self._line[1]
        num_args = self._line[2]
        return_idx = self._idx + 1
        cmd_lst = []

        # push (RETURN_<return_idx>)
        cmd_lst.append(['push', 'constant', f'RETURN_{return_idx}'])

        # push local, argument, this, that
        for i in range(-2, 2, 1):
            cmd_lst.append(['push', 'pointer', f'{i}'])

        # argument = SP - 5 - <num_args>
        cmds = [['push', 'pointer', '-3'],
                ['push', 'constant', '5'],
                ['sub'],
                ['push', 'constant', num_args],
                ['sub'],
                ['pop', 'pointer', '-1']]
        cmd_lst.extend(cmds)

        # local = SP
        cmds = [['push', 'pointer', '-3'],
                ['pop', 'pointer', '-2']]
        cmd_lst.extend(cmds)

        cmd_lst.append(['goto', func_name])
        cmd_lst.append(['label', f'RETURN_{return_idx}'])

        # translating the resulting list of VM commands
        for line in cmd_lst:
            line_translator = Translator(line_lst=line)
            line_translator.translate()
        
        return ''

    def _return(self, raw_code):
        '''
        Processes the RETURN command.
        Loads previously saved frame of the former function.
        Jumps to the next instruction after the corresponding CALL command
        '''
        sp_addr = 14
        ret_addr = 15
        cmd_lst = []

        # R<ret_addr> = *(local - 5)
        cmds = [['push', 'local', '-5'],
                ['pop', 'pointer', f'{ret_addr - 3}']]
        cmd_lst.extend(cmds)

        # *argument = pop()
        cmd_lst.append(['pop', 'argument', '0'])

        # R<sp_addr> = argument + 1
        cmds = [['push', 'pointer', '-1'],
                ['push', 'constant', '1'],
                ['add'],
                ['pop', 'pointer', f'{sp_addr - 3}']]
        cmd_lst.extend(cmds)

        # that = *(local - 1)
        cmds = [['push', 'local', '-1'],
                ['pop', 'pointer', '1']]
        cmd_lst.extend(cmds)

        # this = *(local - 2)
        cmds = [['push', 'local', '-2'],
                ['pop', 'pointer', '0']]
        cmd_lst.extend(cmds)
        
        # argument = *(local - 3)
        cmds = [['push', 'local', '-3'],
                ['pop', 'pointer', '-1']]
        cmd_lst.extend(cmds)

        # local = *(local - 4)
        cmds = [['push', 'local', '-4'],
               ['pop', 'pointer', '-2']]
        cmd_lst.extend(cmds)

        # SP = R<sp_addr>
        cmds = [['push', 'pointer', f'{sp_addr - 3}'],
                ['pop', 'pointer', '-3']]
        cmd_lst.extend(cmds)

        # translating the resulting list of VM commands
        for line in cmd_lst:
            line_translator = Translator(line_lst=line)
            line_translator.translate()

        # substitute placeholders for the corresponding strings
        formatted_code = raw_code.format(var_1 = ret_addr)

        return formatted_code + '\n'        


class Parser:
    '''
    Takes a string which represents one line of a VM code.
    Removes all the whitespaces and ignores comments.
    Returns a list of strings-words that define an operation. 
    '''
    def __init__(self, line_str):
        self._line = line_str
        self._line_lst = []

    def parse(self):
        self._remove_comm_()
        self._line_lst = self._line.split()

    def _remove_comm_(self):
        if '/' in self._line:
            ind = self._line.index('/')
            self._line = self._line[:ind]

    @property
    def output(self):
        return self._line_lst


def vm_parser(dir):

    parsed_vm = []
    has_init = False

    for filename in os.listdir(dir):
        vm_file_loc = os.path.join(dir, filename)
        # reading the .vm file line-by-line
        if os.path.isfile(vm_file_loc):
            with open(vm_file_loc, 'r', encoding='utf-8') as input_file:
                for line in input_file:
                    # parse a single line into a list of strings
                    line_parser = Parser(line)
                    line_parser.parse()
                    parsed_line = line_parser.output
                    # if it is an instruction, add it to the output
                    if len(parsed_line) > 0:
                        parsed_vm.append(parsed_line)
                        # put a flag if .init function is detected
                        if parsed_line[0] == 'function':
                            if parsed_line[1] == 'Sys.init':
                                has_init = True

    return parsed_vm, has_init


def main():

    # computing paths to internal directories
    curr_dir = os.getcwd()
    vm_dir = os.path.join(curr_dir, 'VM_instructions')
    asm_dir = os.path.join(curr_dir, 'ASM_code')
    pattern_dir = os.path.join(curr_dir, 'patterns')
    
    # computing absolute path to the .asm output file
    asm_filename = 'output.asm'
    asm_file_loc = os.path.join(asm_dir, asm_filename)

    # loading operation patterns into translator
    Translator.create_mappings(pattern_dir)

    # print(Translator.report_state())

    parsed_vm, has_init = vm_parser(vm_dir)

    if has_init:
        parsed_vm.insert(0, ['goto', 'Sys.init'])
        curr_class = 'Sys'
    else:
        curr_class = ''

    for idx, line in enumerate(parsed_vm):
        if line[0] == 'function':
            curr_class = line[1].split('.')[0]
        line_translator = Translator(line, curr_class, idx)
        line_translator.translate()

    # getting result of translation
    asm_out = Translator.get_output()

    # writing result to the output file
    with open(asm_file_loc, 'w', encoding='utf-8') as out_f:
        out_f.write(asm_out)


if __name__ == '__main__':

    print('\n<<< SCRIPT START >>>\n')

    main()

    print('\n<<< SCRIPT END >>>\n')