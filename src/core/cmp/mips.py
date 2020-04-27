import core.cmp.visitor as visitor

ATTR_SIZE = 4

class Node:
    pass

class ProgramNode(Node):
    def __init__(self, dottext, dotdata, types):
        self._dottext = dottext
        self._dotdata = dotdata


class FunctionNode(Node):
    def __init__(self, instructions):
        self.instructions = instructions

class DataNode(Node):
    def __init__(self, name, value):
        self.name  = name
        self.value = value

class InstructionNode(Node):
    pass

class LabelNode(InstructionNode):
    def __init__(self, name):
        self.name = name

class MoveNode(InstructionNode):
    def __init__(self, reg1, reg2):
        self.reg1 = reg1
        self.reg2 = reg2

class LoadInmediateNode(InstructionNode):
    def __init__(self, reg, value):
        self.reg = reg
        self.value = value

class LoadWordNode(InstructionNode):
    def __init__(self, reg, addr):
        self.reg = reg
        self.addr = addr

class SyscallNode(InstructionNode):
    pass

class LoadAddressNode(InstructionNode):
    def __init__(self, reg, label):
        self.reg = reg
        self.label = label

class StoreWordNode(InstructionNode):
    def __init__(self, reg, addr):
        self.reg = reg
        self.addr = addr

class JumpAndLinkNode(InstructionNode):
    def __init__(self, label):
        self.label = label

class JumpRegister(InstructionNode):
    def __init__(self, reg):
        self.reg = reg





class MIPSType():
    def __init__(self, name, attributes, methods):
        self.attributes = attributes
        self.methods = methods

    def get_attr_offset(self, attr_name):
        return ATTR_SIZE * self.attributes.index(attributes)
    
    def get_func(self, method_name):
        return self.methods[method_name]
    
    @property
    def size(self):
        return len(self.attributes) * ATTR_SIZE 

