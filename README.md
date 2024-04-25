# ipp23interpret

## 📚 Introduction

This is IPP project 2 from 2023.

`interpret.py` is a script that has three arguments, help, source, and input, where the source accepts a file
with XML code. The script will perform the check and execute the individual instructions at the same time. In case of errors,
exit the program with the desired return number.

## 📃 Program

Arguments are processed first in the `main` function using `getopt`. Either help or is displayed
the program exits or switches to the interpreter. If the source or input is not specified, it will require the user to enter a path. Input will only be requested if the instruction is READ.
If you `switch` to the interpreter, the XML code is first processed using the `ElementTree` library. After that
check to see if it starts with a program tag. An instance of a class is created using a `for-loop`
Instruction and is stored in an array. At the same time, the XML semantics is checked when saving the instructions.
Using the for loop, all `LABEL` instructions are found, and an instance of the Label class is created for them
and stored in the labels field.
In the end, the instructions are just executed. The opcode is used to decide which it will be executed.

### Auxiliary functions

The script contains some helper functions.
`file_existence` - checks for existence function
`select_frame` – selects the desired frame according to the variable
`replace` – replacement of one character at a certain position of the string
`arithmetic` – performs the selected arithmetic operation
`get_type` – decides the type and returns it with a value in the correct format
`modify_bool` – converts bool to lowercase
`modify_string` – modifies the string and replaces the `\xyz` format with the corresponding character
`do_instruction` – the main function according to which it is decided what should be executed

The main part of the script is the do_instruction function, which uses a condition to decide what to do next
script function.

### Classes

The `Instraction` class defines the name, sequence number, and argument array of the instruction. Using the function
`add_arg` inserts a new `Arg` instance into `args`, defining the type and name. The `Frame` class defines
the frame_records array containing the instance of the FrameRecord class. Whenever it is performed
any instruction, the `selec_frame` function is used to decide which frame to work with.
This is decided using the variable name. Subsequently, using the function in `Frame` search_record
finds the given transformation and returns. Only if the instruction is `DEFVAR` is the parameter `defvar`
set to True.
The insert_record function inserts a new record into the frame and the modify_record function modifies an existing one
record.

Finding the value of `GF@a` in the global frame:
`selected_frame = select_frame(args[1]) # args[1]` is an instance of the class
Arg stored in the args array at the first position
`record = selected_frame.search_record(args[1])`
To modify the value of `GF@a` in the global framework:
`selected_frame.modify_record(record, name, new_type, new_value)`
If the argument type is var, you need to access a certain frame and only then execute a certain one
instruction (e.g. `MOVE GF@a GF@b`)
```
If args[2].arg_type == 'var':
selected_frame = selected_frame(args[2])
. . .
```
In the case of `CREATEFRAME`, a new `Frame` is initialized into the `temp_frame` variable. After execution
`PUSHFRAME`, the variables are renamed from `TF` to `LF` and the `temp_frame` variable is inserted into the array
`local_frames` and set to None. If it comes to `POPFRAME`, the same thing is done, only
the variables are renamed to `TF` and a pop to `temp_frame` is performed.
The `Stack` and `StackData` classes define how the data stack behaves. In `StackData` we store the type
and the name and in the `Stack` list stack with `StackData` instances. The stack contains `stack_push` functions
to insert new data and `stack_pop` to pop it out. These invoke the `PUSHS` and `POPS` instructions

### Uml Diagram

<img src="https://github.com/Biliator/ipp23interpret/blob/main/uml.png" alt="uml">

### Jumps

In order to make jumps in the program, the sequence number of the instruction is kept in the index all the time.
If there is a jump request. The labels field contains a specific Label initialization with the name on which
is to be jumped, its number is taken and set as an index.
The rest of the instructions work on approximately the same principle.

## ⚖️ License

See [LICENSE](LICENSE).
