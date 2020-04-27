import core.cmp.visitor as visitor
from core.cmp.CoolUtils import *
from core.cmp.semantic import SemanticError
from core.cmp.semantic import Attribute, Method, Type
from core.cmp.semantic import ErrorType, IntType, StringType, BoolType, IOType, VoidType
from core.cmp.semantic import Context, Scope

WRONG_SIGNATURE = 'Method "%s" already defined in "%s" with a different signature.'
SELF_IS_READONLY = 'Variable "self" is read-only.'
LOCAL_ALREADY_DEFINED = 'Variable "%s" is already defined in method "%s".'
INCOMPATIBLE_TYPES = 'Cannot convert "%s" into "%s".'
VARIABLE_NOT_DEFINED = 'Variable "%s" is not defined.'
INVALID_OPERATION = 'Operation is not defined between "%s" and "%s".'
CONDITION_NOT_BOOL = '"%s" conditions return type must be Bool not "%s"'

ST, AT = ['SELF_TYPE', 'AUTO_TYPE']
sealed = ['Int', 'String', 'Bool', 'SELF_TYPE', 'AUTO_TYPE']
built_in_types = [ 'Int', 'String', 'Bool', 'Object', 'IO', 'SELF_TYPE', 'AUTO_TYPE']

def define_built_in_types(context):
    obj = context.create_type('Object')
    i = context.create_type('Int')
    i.set_parent(obj)
    s = context.create_type('String')
    s.set_parent(obj)
    context.create_type('Bool').set_parent(obj)
    io = context.create_type('IO')
    io.set_parent(obj)
    st = context.create_type('SELF_TYPE')
    context.create_type('AUTO_TYPE')

    obj.define_method('abort', [], [], obj)
    obj.define_method('type_name', [], [], s)
    obj.define_method('copy', [], [], st)

    io.define_method('out_string', ['x'], [s], st)
    io.define_method('out_int', ['x'], [i], st)
    io.define_method('in_string', [], [], s)
    io.define_method('in_int', [], [], i)

    s.define_method('length', [], [], i)
    s.define_method('concat', ['s'], [s], s)
    s.define_method('substr', ['i', 'l'], [i, i], s)

def match(type1, type2):
    return IsAuto(type1.name) or type1.conforms_to(type2)

def fixed_type(type1, type2):
    return type1 if type1.name != ST else type2

#AST Printer
class FormatVisitor:
    @visitor.on('node')
    def visit(self, node, tabs):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__ProgramNode [<class> ... <class>]'
        statements = '\n'.join(self.visit(child, tabs + 1) for child in node.declarations)
        return f'{ans}\n{statements}'
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node, tabs=0):
        parent = '' if node.parent is None else f"inherits {node.parent}"
        ans = '\t' * tabs + f'\\__ClassDeclarationNode: class {node.id} {parent} {{ <feature> ... <feature> }}'
        features = '\n'.join(self.visit(child, tabs + 1) for child in node.features)
        return f'{ans}\n{features}'
    
    @visitor.when(AttrDeclarationNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] if node.expr else []
        text = '<- <expr>' if node.expr else ''
        ans = '\t' * tabs + f'\\__AttrDeclarationNode: {node.id} : {node.type} {text}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}' if body else f'{ans}'
    
    @visitor.when(FuncDeclarationNode)
    def visit(self, node, tabs=0):
        params = ', '.join(':'.join(param) for param in node.params)
        ans = '\t' * tabs + f'\\__FuncDeclarationNode: {node.id}({params}) : {node.type} {{<body>}}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in node.body)
        return f'{ans}\n{body}'
    
    @visitor.when(IfThenElseNode)
    def visit(self, node, tabs=0):
        sons = [node.condition, node.if_body]
        text = ''
        if node.else_body:
            sons.append(node.else_body)
            text += 'else <body>'
        ans = '\t' * tabs + f'\\__IfThenElseNode: if <cond> then <body> {text} fi'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(WhileLoopNode)
    def visit(self, node, tabs=0):
        sons = [node.condition, node.body]
        ans = '\t' * tabs + f'\\__WhileLoopNode: while <cond> loop <body> pool'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(BlockNode)
    def visit(self, node, tabs=0):
        sons = node.exprs
        ans = '\t' * tabs + f'\\__BlockNode: {{<expr> ... <expr>}}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(LetInNode)
    def visit(self, node, tabs=0):
        sons = node.let_body + [node.in_body]
        ans = '\t' * tabs + f'\\__LetInNode: let {{<attr> ... <attr>}} in <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(CaseOfNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] + node.branches
        ans = '\t' * tabs + f'\\__CaseOfNode: case <expr> of {{<case> ... <case>}} esac'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(CaseExpressionNode)
    def visit(self, node, tabs=0):
        sons = [node.expr]
        ans = '\t' * tabs + f'\\__CaseExpressionNode: {node.id} : {node.type} => <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'

    @visitor.when(LetAttributeNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] if node.expr else []
        text = '<- <expr>' if node.expr else ''
        ans = '\t' * tabs + f'\\__LetAttributeNode: {node.id} : {node.type} {text}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}' if body else f'{ans}'
    
    @visitor.when(AssignNode)
    def visit(self, node, tabs=0):
        sons = [node.expr]
        ans = '\t' * tabs + f'\\__AssignNode: {node.id} = <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(UnaryNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__{node.__class__.__name__} <expr>'
        right = self.visit(node.expr, tabs + 1)
        return f'{ans}\n{right}'
   
    @visitor.when(BinaryNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__<expr> {node.__class__.__name__} <expr>'
        left = self.visit(node.left, tabs + 1)
        right = self.visit(node.right, tabs + 1)
        return f'{ans}\n{left}\n{right}'

    @visitor.when(AtomicNode)
    def visit(self, node, tabs=0):
        return '\t' * tabs + f'\\__ {node.__class__.__name__}: {node.lex}'
    
    @visitor.when(FunctionCallNode)
    def visit(self, node, tabs=0):
        obj = self.visit(node.obj, tabs + 1)
        ans = '\t' * tabs + f'\\__FunctionCallNode: <obj>.{node.id}(<expr>, ..., <expr>)'
        args = '\n'.join(self.visit(arg, tabs + 1) for arg in node.args)
        return f'{ans}\n{obj}\n{args}'

    @visitor.when(MemberCallNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__MemberCallNode: {node.id}(<expr>, ..., <expr>)'
        args = '\n'.join(self.visit(arg, tabs + 1) for arg in node.args)
        return f'{ans}\n{args}'
    
    @visitor.when(NewNode)
    def visit(self, node, tabs=0):
        return '\t' * tabs + f'\\__NewNode: new {node.type}()'

# Type Collector
class TypeCollector:
    def __init__(self, errors=[]):
        self.context = None
        self.errors = errors
        self.type_level = {}
        self.parent = {}
    
    @visitor.on('node')
    def visit(self, node):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node):
        self.context = Context()
        define_built_in_types(self.context)
        
        for def_class in node.declarations:
            self.visit(def_class)
             
        # comparison for sort node.declarations
        def get_type_level(typex):
            try:
                parent = self.type_level[typex]
            except KeyError:
                return 0
            
            if parent == 0:
                node = self.parent[typex]
                node.parent = "Object"
                self.errors.append(('Cyclic heritage.', node.tparent))
            elif type(parent) is not int:
                self.type_level[typex] = 0 if parent else 1
                if type(parent) is str:
                    self.type_level[typex] = get_type_level(parent) + 1
                
            return self.type_level[typex]
        
        node.declarations.sort(key = lambda node: get_type_level(node.id))               
                
    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        def new_type():
            self.context.create_type(node.id)
            self.type_level[node.id] = node.parent
            self.parent[node.id] = node

        def make_a_duplicate():
            while True:
                node.id = '1' + node.id
                try: new_type()
                except SemanticError: pass
                else: break

        if node.id not in built_in_types:
            try: new_type()
            except SemanticError as ex:
                self.errors.append((ex.text, node.tid))
                make_a_duplicate()
        else:
            self.errors.append((f'{node.id} is an invalid class name', node.tid))
            make_a_duplicate()

# Type Builder
class TypeBuilder:
    def __init__(self, context, errors=[]):
        self.context = context
        self.current_type = None
        self.errors = errors
        self.methods = {}
    
    @visitor.on('node')
    def visit(self, node):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node):
        main_token = None
        for def_class in node.declarations:
            self.visit(def_class)
            if def_class.id == 'Main':
                main_token = def_class.tid
            
        try:
            main = self.context.get_type('Main')
            method = main.methods['main']
            tmethod = self.methods['Main']['main']
            if method.param_names:
                self.errors.append(('Method "main" must takes no formal parameters', tmethod))
        except SemanticError:
            self.errors.append(('No definition for class "Main"', empty_token))
        except KeyError:
            self.errors.append(('Class "Main" must have a method "main"', main_token))         
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        self.current_type = self.context.get_type(node.id)
        
        if node.parent:
            if node.parent in sealed:
                self.errors.append((f'Is not possible to inherits from "{node.parent}"', node.tparent))
                node.parent = 'Object'
            try:
                parent_type = self.context.get_type(node.parent)
                self.current_type.set_parent(parent_type)
            except SemanticError as ex:
                self.errors.append((ex.text, node.tparent))
        
        for feature in node.features:
            self.visit(feature)
            
    @visitor.when(AttrDeclarationNode)
    def visit(self, node):
        try:
            attr_type = self.context.get_type(node.type)
        except SemanticError as ex:
            self.errors.append((ex.text, node.ttype))
            attr_type = ErrorType()
        node.attr_type = attr_type

        try:
            self.current_type.define_attribute(node.id, attr_type)
        except SemanticError as ex:
            self.errors.append((ex.text, node.tid))
        
    @visitor.when(FuncDeclarationNode)
    def visit(self, node):
        arg_names, arg_types = [], []
        for i, (idx, typex) in enumerate(node.params):
            try:
                arg_type = self.context.get_type(typex)
            except SemanticError as ex:
                self.errors.append((ex.text, node.params[i].ttype))
                arg_type = ErrorType()
                
            arg_names.append(idx)
            arg_types.append(arg_type)
        
        try:
            ret_type = self.context.get_type(node.type)
        except SemanticError as ex:
            self.errors.append((ex.text, node.ttype))
            ret_type = ErrorType()
        node.ret_type = ret_type
        node.arg_types = arg_types
        node.arg_names = arg_names

        try:
            self.current_type.define_method(node.id, arg_names, arg_types, ret_type)
            if not self.current_type.name in self.methods:
                self.methods[self.current_type.name] = {}
            self.methods[self.current_type.name][node.id] = node.tid    
        except SemanticError as ex:
            self.errors.append((ex.text, node.tid))

# Compute the Lowest Common Ancestor in
# the type hierarchy tree
def LCA(type_list, context):
    known_types = set()
    counter = {}

    type_list = [ context.get_type(tp.name) for tp in type_list ]
    for typex in type_list:
        node = typex
        while True:
            try:
                counter[node.name] += 1
                if counter[node.name] == len(type_list):
                    return [t for t in known_types if t.name == node.name][0]
            except KeyError:
                counter[node.name] = 1
                known_types.add(node)
            if node.parent:
                node = node.parent
            else:
                break

    raise Exception('El LCA se partio')

def IsAuto(name):
    return name == 'AUTO_TYPE' or IsVoid(name)

def IsVoid(name):
    return name == 'void'

# Type Checker
class TypeChecker:
    def __init__(self, context, errors=[]):
        self.context = context
        self.current_type = None
        self.current_method = None
        self.errors = errors

    @visitor.on('node')
    def visit(self, node, scope):
        pass

    @visitor.when(ProgramNode)
    def visit(self, node, scope=None):
        scope = Scope()
        for declaration in node.declarations:
            self.visit(declaration, scope.create_child())
        return scope

    @visitor.when(ClassDeclarationNode)
    def visit(self, node, scope):
        self.current_type = self.context.get_type(node.id)
        
        scope.define_variable('self', self.current_type)
        for attr in self.current_type.attributes:
            scope.define_variable(attr.name, attr.type)
            
        for feature in node.features:
            self.visit(feature, scope.create_child())
    
    @visitor.when(AttrDeclarationNode)
    def visit(self, node, scope):
        if not node.expr:
            return

        self.visit(node.expr, scope)
        expr_type = fixed_type(node.expr.computed_type, self.current_type)
        real_type = fixed_type(node.attr_type, self.current_type)

        # //TODO: SELF_TYPE match every type???
        if not expr_type.conforms_to(real_type):
            self.errors.append((INCOMPATIBLE_TYPES % (expr_type.name, real_type.name),  node.arrow))
            
    @visitor.when(FuncDeclarationNode)
    def visit(self, node, scope):
        self.current_method = Method(node.id, node.arg_names, node.arg_types, node.ret_type)
        
        for pname, ptype in zip(self.current_method.param_names, self.current_method.param_types):
            scope.define_variable(pname, ptype)
            
        # for expr in node.body:
        self.visit(node.body, scope)
            
        body_type = fixed_type(node.body.computed_type, self.current_type)
        method_rtn_type = fixed_type(self.current_method.return_type, self.current_type)

        # //TODO: be carefull whit void
        if not match(body_type, method_rtn_type):
            self.errors.append((INCOMPATIBLE_TYPES % (body_type.name, method_rtn_type.name), node.ttype))
            
    @visitor.when(AssignNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        expr_type = fixed_type(node.expr.computed_type, self.current_type)
        
        if scope.is_defined(node.id):
            var = scope.find_variable(node.id)
            node_type = var.type      
            var_type = fixed_type(node_type, self.current_type) 
            
            if var.name == 'self':
                self.errors.append((SELF_IS_READONLY, node.tid))
            elif not expr_type.conforms_to(var_type): 
                self.errors.append((INCOMPATIBLE_TYPES % (expr_type, var_type), node.tid))
        else:
            self.errors.append((VARIABLE_NOT_DEFINED % (node.id), node.tid))
            node_type = ErrorType()
        
        node.computed_type = node_type
        
    @visitor.when(CaseOfNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        
        types_list = []
        for case in node.branches:
            self.visit(case.expr, scope.create_child())
        # The return type of a <case of> is unknown until runtime 
        node.computed_type = ErrorType()

    @visitor.when(CaseExpressionNode)
    def visit(self, node, scope):
        try:
            branch_type = self.context.get_type(node.type)
        except SemanticError as ex:
            self.errors.append((ex.text, node.ttype))
            branch_type = ErrorType()
        scope.define_variable(node.id, branch_type)
        self.visit(node.expr, scope)
        node.computed_type = node.expr.computed_type
            
    @visitor.when(LetInNode)
    def visit(self, node, scope):
        child = scope.create_child()
        node.scope = child
        
        for expr in node.let_body:
            self.visit(expr, child)
            
        self.visit(node.in_body, child)
        node.computed_type = node.in_body.computed_type

    @visitor.when(LetAttributeNode)
    def visit(self, node, scope):
        try:
            node_type = self.context.get_type(node.type)
        except SemanticError as ex:
            self.errors.append((ex.text, node.ttype))
            node_type = ErrorType()

        if not scope.is_local(node.id):
            scope.define_variable(node.id, node_type)
        else:
            self.errors.append((LOCAL_ALREADY_DEFINED % (node.id, self.current_method.name), node.tid))
        
        if node.expr:
            self.visit(node.expr, scope)
            expr_type = fixed_type(node.expr.computed_type, self.current_type)
            real_type = fixed_type(node_type, self.current_type)
            
            if not expr_type.conforms_to(real_type): 
                self.errors.append((INCOMPATIBLE_TYPES % (expr_type.name, real_type.name), node.arrow))
        
    @visitor.when(IfThenElseNode)
    def visit(self, node, scope):
        self.visit(node.condition, scope)
        cond_type = fixed_type(node.condition.computed_type, self.current_type)

        if BoolType() != cond_type:
            self.errors.append((CONDITION_NOT_BOOL % ('If', cond_type.name), node.token))

        self.visit(node.if_body, scope)
        if node.else_body:
            self.visit(node.else_body, scope)
        # The return type of a <if> is unknown until runtime 
        node.computed_type = ErrorType()
        
    @visitor.when(BlockNode)
    def visit(self, node, scope):
        for expr in node.exprs:
            self.visit(expr, scope)

        last_expr = node.exprs[-1]
        node.computed_type = last_expr.computed_type    
            
    @visitor.when(WhileLoopNode)
    def visit(self, node, scope):
        self.visit(node.condition, scope)
        cond_type = fixed_type(node.condition.computed_type, self.current_type)

        if BoolType() != cond_type::
            self.errors.append((CONDITION_NOT_BOOL % ('While', cond_type.name), node.token))

        self.visit(node.body, scope)
        node.computed_type = VoidType()
    
    @visitor.when(FunctionCallNode)
    def visit(self, node, scope):
        self.visit(node.obj, scope)
        obj_type = fixed_type(node.obj.computed_type, self.current_type)
        
        error = False

        arg_types = []
        for arg in node.args:
            self.visit(arg, scope)
            arg = fixed_type(arg.computed_type, self.current_type)
            arg_types.append(arg)
        
        try:
            if node.type:
                token = node.ttype
                cast_type = self.context.get_type(node.type)
                if cast_type.name == ST:
                    raise SemanticError("Invalid use of SELF_TYPE")
                # if IsAuto(node.type):
                #     raise SemanticError('Is not possible to use AUTO_TYPE in a cast')
                if not obj_type.conforms_to(cast_type):
                    raise SemanticError(INCOMPATIBLE_TYPES % (obj_type.name, node.type))
                obj_type = cast_type
            
            token = node.tid
            obj_method = obj_type.get_method(node.id)
            if len(node.args) == len(obj_method.param_types):
                for idx, (arg, param_type) in enumerate(zip(arg_types, obj_method.param_types)):
                    real_type = fixed_type(param_type, self.current_type)
                    
                    if not arg.conforms_to(real_type):
                        self.errors.append((INCOMPATIBLE_TYPES % (arg.name, real_type.name + f" in the argument #{idx} of {node.id}"), token))
                        error = True
            else:
                raise SemanticError(f'Method "{obj_method.name}" of "{obj_type.name}" only accepts {len(obj_method.param_types)} argument(s)')
            assert error
            node_type = obj_method.return_type
        except SemanticError as ex:
            self.errors.append((ex.text, token))
            node_type = ErrorType()
        except AssertionError:
            node_type = ErrorType()
            
        node.computed_type = node_type

    @visitor.when(MemberCallNode)
    def visit(self, node, scope):
        obj_type = self.current_type
        
        error = False

        arg_types = []
        for arg in node.args:
            self.visit(arg, scope)
            arg = fixed_type(arg.computed_type, self.current_type)
            arg_types.append(arg)

        try:
            token = node.tid
            obj_method = obj_type.get_method(node.id)
            if len(node.args) == len(obj_method.param_types):
                for arg, param_type in zip(node.args, obj_method.param_types):
                    real_type = fixed_type(param_type, self.current_type)
                    
                    if not arg.conforms_to(real_type):
                        self.errors.append((INCOMPATIBLE_TYPES % (arg.name, real_type.name + f" in the argument #{idx} of {node.id}"), token))
                        error = True
            else:
                raise SemanticError(f'Method "{obj_method.name}" of "{obj_type.name}" only accepts {len(obj_method.param_types)} argument(s)')
            assert error
            node_type = obj_method.return_type
        except SemanticError as ex:
            self.errors.append((ex.text, token))
            node_type = ErrorType()
        except AssertionError:
            node_type = ErrorType()
            
        node.computed_type = node_type
    
    @visitor.when(ArithmeticNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = fixed_type(node.left.computed_type, self.current_type)
        
        self.visit(node.right, scope)
        right_type = fixed_type(node.right.computed_type, self.current_type)
        
        if IntType() != right_type or IntType() != left_type:
            self.errors.append((INVALID_OPERATION % (left_type.name, right_type.name), node.symbol))
            node_type = ErrorType()
        else:
            node_type = IntType()
            
        node.computed_type = node_type
    
    @visitor.when(ComparisonNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = fixed_type(node.left.computed_type, self.current_type)
        
        self.visit(node.right, scope)
        right_type = fixed_type(node.right.computed_type, self.current_type)
        
        if BoolType() != right_type or BoolType() != left_type:
            self.errors.append((INVALID_OPERATION % (left_type.name, right_type.name), node.symbol))
            node_type = BoolType()
        else:
            node_type = BoolType()
            
        node.computed_type = node_type

    @visitor.when(IntegerNode)
    def visit(self, node, scope):
        node.computed_type = IntType()
        
    @visitor.when(StringNode)
    def visit(self, node, scope):
        node.computed_type = StringType()
        
    @visitor.when(BoolNode)
    def visit(self, node, scope):
        node.computed_type = BoolType()

    @visitor.when(IdNode)
    def visit(self, node, scope):
        if scope.is_defined(node.lex):
            var = scope.find_variable(node.lex)
            node_type = var.type       
        else:
            self.errors.append(VARIABLE_NOT_DEFINED.replace('%s', node.lex, 1))
            node_type = ErrorType()
        
        node.computed_type = node_type

    @visitor.when(NewNode)
    def visit(self, node, scope):
        if node.type in built_in_types[:3]:
            self.errors.append(f'It cannot be initialized a {node.type} with the new keyword')
            node.computed_type = ErrorType()
        else:
            try:
                node_type = self.context.get_type(node.type)
            except SemanticError as ex:
                self.errors.append(ex.text)
                node_type = ErrorType()
                
            node.computed_type = node_type

    @visitor.when(IsVoidNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        node.computed_type = self.context.get_type('Bool')

    @visitor.when(ComplementNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        if node.expr.computed_type.name != 'Int':
            self.errors.append("Complement works only for Int")
            node.computed_type = ErrorType()
        else:
            node.computed_type = self.context.get_type('Int')

    @visitor.when(NotNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        if node.expr.computed_type.name != 'Bool':
            self.errors.append("Not operator works only for Bool")
            node.computed_type = ErrorType()
        else:
            node.computed_type = self.context.get_type('Bool')

    @visitor.when(EqualNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = node.left.computed_type
        
        self.visit(node.right, scope)
        right_type = node.right.computed_type
        
        if not (left_type.name == right_type.name and left_type.name in built_in_types[:3]):
            self.errors.append(INVALID_OPERATION.replace('%s', left_type.name, 1).replace('%s', right_type.name, 1))
            node_type = ErrorType()
        else:
            node_type = right_type
            
        node.computed_type = node_type

# Type Inference Visitor
class InferenceVisitor(TypeChecker):
    def __init__(self, context, errors=[]):
        self.context = context
        self.current_type = None
        self.current_method = None
        self.errors = errors

    @visitor.on('node')
    def update(self, node, scope, ntype):
    	pass

    @visitor.when(FunctionCallNode)
    def update(self, node, scope, ntype):
        obj_type = node.obj.computed_type

        obj_type.get_method(node.id).return_type = ntype
        node.computed_type = ntype

    @visitor.when(MemberCallNode)
    def update(self, node, scope, ntype):
        obj_type = self.current_type

        obj_type.get_method(node.id).return_type = ntype
        node.computed_type = ntype

    @visitor.when(AttrDeclarationNode)
    def update(self, node, scope, ntype):
    	scope.find_variable(node.id).type = ntype
    	node.computed_type = ntype

    @visitor.when(IdNode)
    def update(self, node, scope, ntype):
    	scope.find_variable(node.lex).type = ntype
    	node.computed_type = ntype

    @visitor.when(IfThenElseNode)
    def update(self, node, scope, ntype):
        if IsAuto(node.if_body.computed_type.name):
            self.update(node.if_body, scope, ntype)

        node.computed_type = node.if_body.computed_type

        if node.else_body:
            if IsAuto(node.else_body.computed_type.name):
                self.update(node.else_body, scope, ntype)

            names = [node.if_body.computed_type.name, node.else_body.computed_type.name]
            if 'AUTO_TYPE' not in names and '<error>' not in names:
                types_list = [node.if_body.computed_type, node.else_body.computed_type]
                if all([t.name == ST for t in types_list]):
                    node.computed_type = types_list[0]
                else:
                    node.computed_type = LCA([fixed_type(t, self.current_type) for t in types_list], self.context)
            else:
                if '<error>' in names:
                    node.computed_type = ErrorType()
                else:
                    node.computed_type = self.context.get_type('AUTO_TYPE')
    
    @visitor.when(CaseOfNode)
    def update(self, node, scope, ntype):
        types_list = []
        has_auto = has_error = False

        for case in node.branches:
            if IsAuto(case.computed_type.name):
                self.update(branch, scope, ntype)
                has_auto |= IsAuto(case.expr.computed_type.name)
                has_error |= case.expr.computed_type.name == '<error>'
                types_list.append(case.expr.computed_type)
        
        if has_error:
            node.computed_type = ErrorType()
        elif has_auto:
            node.computed_type = self.context.get_type('AUTO_TYPE')
        else:
            if all([t.name == ST for t in types_list]):
                node.computed_type = types_list[0]
            else:
                node.computed_type = LCA([fixed_type(t, self.current_type) for t in types_list], self.context)

    @visitor.when(CaseExpressionNode)
    def update(self, node, scope, ntype):
        self.update(node.expr, scope, ntype)
        node.computed_type = node.expr.computed_type

    @visitor.when(LetInNode)
    def update(self, node, scope, ntype):
        self.update(node.in_body, node.scope, ntype)
        node.computed_type = node.in_body.computed_type

    @visitor.when(BlockNode)
    def update(self, node, scope, ntype):
        self.update(node.exprs[-1], scope, ntype)
        node.computed_type = node.exprs[-1].computed_type

    @visitor.on('node')
    def visit(self, node, scope):
        pass
    
    @visitor.when(Node)
    def visit(self, node, scope):
        super().visit(node, scope)
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node, scope):
        super().visit(node, scope)

        for idx, attr in enumerate(self.current_type.attributes):
            actual_type = scope.find_variable(attr.name).type
            if IsAuto(attr.type.name):
                self.current_type.attributes[idx].type = actual_type
    
    @visitor.when(AttrDeclarationNode)
    def visit(self, node, scope):
        node.scope = scope
        if node.expr:
            self.visit(node.expr, scope)
            if IsAuto(node.type):
                if not IsAuto(node.expr.computed_type.name):
                    scope.find_variable(node.id).type = node.expr.computed_type
                    node.computed_type = node.expr.computed_type
            else:
                if IsAuto(node.expr.computed_type.name):
                    self.update(node.expr, scope, node.type)
                else:
                    if not node.expr.computed_type.conforms_to(node.computed_type):
                        self.errors.append(INCOMPATIBLE_TYPES.replace('%s', expr_type.name, 1).replace('%s', node_type.name, 1))
                        node.computed_type = ErrorType()			

    @visitor.when(FuncDeclarationNode)
    def visit(self, node, scope):
        self.current_method = self.current_type.get_method(node.id)
        node.method = self.current_method

        for pname, ptype in zip(self.current_method.param_names, self.current_method.param_types):
            scope.define_variable(pname, ptype)

        # for expr in node.body:
        self.visit(node.body, scope)

        last_expr = node.body
        last_expr_type = last_expr.computed_type
        method_rtn_type = self.current_method.return_type    

        if IsAuto(method_rtn_type.name):
            if not IsAuto(last_expr_type.name):
                self.current_method.return_type = last_expr_type
                method_rtn_type = last_expr_type
        else:
            if IsAuto(last_expr_type.name):
                self.update(last_expr, scope, method_rtn_type)
            else:
                if not last_expr_type.conforms_to(method_rtn_type):
                    self.errors.append(INCOMPATIBLE_TYPES.replace('%s', last_expr_type.name, 1).replace('%s', method_rtn_type.name, 1))
            
        for idx, pname in enumerate(self.current_method.param_names):
            actual_type = scope.find_variable(pname).type
            if self.current_method.param_types[idx].name != actual_type.name:
                self.current_method.param_types[idx] = actual_type
    
    @visitor.when(IfThenElseNode)
    def visit(self, node, scope):
        self.visit(node.condition, scope)
        expr_type = node.condition.computed_type

        if IsAuto(expr_type.name):
            self.update(node.condition, scope, self.context.get_type('Bool'))
            expr_type = node.condition.computed_type
        if expr_type.name not in ['Bool', 'AUTO_TYPE']:
            self.errors.append(CONDITION_NOT_BOOL.replace('%s', 'If', 1).replace('%s', expr_type.name, 1))

        self.visit(node.if_body, scope)
        node.computed_type = node.if_body.computed_type

        if node.else_body:
            self.visit(node.else_body, scope)
            names = [node.if_body.computed_type.name, node.else_body.computed_type.name]
            if 'AUTO_TYPE' not in names and '<error>' not in names:
                types_list = [node.if_body.computed_type, node.else_body.computed_type]
                if all([t.name == ST for t in types_list]):
                    node.computed_type = types_list[0]
                else:
                    node.computed_type = LCA([fixed_type(t, self.current_type) for t in types_list], self.context)
            else:
                if '<error>' in names:
                    node.computed_type = ErrorType()
                else:
                    node.computed_type = self.context.get_type('AUTO_TYPE')
    
    @visitor.when(WhileLoopNode)
    def visit(self, node, scope):
        self.visit(node.condition, scope)
        expr_type = node.condition.computed_type
        if IsAuto(expr_type.name):
            self.update(node.condition, scope, self.context.get_type('Bool'))
            expr_type = node.condition.computed_type

        if expr_type.name not in ['Bool', 'AUTO_TYPE']:
            self.errors.append(CONDITION_NOT_BOOL.replace('%s', 'If', 1).replace('%s', expr_type.name, 1))

        self.visit(node.body, scope)
        node.computed_type = VoidType()
    
    @visitor.when(LetInNode)
    def visit(self, node, scope):
        super().visit(node, scope)

        for attr in node.let_body:
            type_name = attr.type
            if attr.computed_type.name == '<error>':
                continue
            actual_type = node.scope.find_variable(attr.id).type
            if type_name != actual_type.name:
                attr.type = actual_type.name

    @visitor.when(LetAttributeNode)
    def visit(self, node, scope):
        node.scope = scope
        try:
            node_type = self.context.get_type(node.type)
        except SemanticError as ex:
            self.errors.append(ex.text)
            node_type = ErrorType()
          
        if not scope.is_local(node.id):
            scope.define_variable(node.id, node_type)
        else:
            self.errors.append(LOCAL_ALREADY_DEFINED.replace('%s', node.id, 1).replace('%s', self.current_method.name, 1))
        
        if not node.expr:
            node.computed_type = node_type
            return

        self.visit(node.expr, scope)
        expr_type = node.expr.computed_type

        if IsAuto(node_type.name):
        	if not IsAuto(expr_type.name):
        		node.type = expr_type.name
        		scope.find_variable(node.id).type = expr_type
        		node.computed_type = expr_type
        else:
            if not IsAuto(expr_type.name):
                if not expr_type.conforms_to(node_type):
                    self.errors.append(INCOMPATIBLE_TYPES.replace('%s', expr_type.name, 1).replace('%s', node_type.name, 1))
            else:
                self.update(node.expr, scope, node_type)
                node.computed_type = node.expr.computed_type

    @visitor.when(AssignNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        expr_type = node.expr.computed_type

        if scope.is_defined(node.id):
            var = scope.find_variable(node.id)
            node_type = var.type       
            
            if var.name == 'self':
                self.errors.append(SELF_IS_READONLY)
            else: 
                if IsAuto(node_type.name):
                    if not IsAuto(expr_type.name):
                        node.type = expr_type.name
                        scope.find_variable(node.id).type = expr_type
                        node.computed_type = expr_type
                else:
                    if not IsAuto(expr_type.name):
                        if not expr_type.conforms_to(node_type):
                            self.errors.append(INCOMPATIBLE_TYPES.replace('%s', expr_type.name, 1).replace('%s', node_type.name, 1))
                    else:
                        self.update(node.expr, scope, node_type)
                        node.computed_type = node.expr.computed_type
        else:
            self.errors.append(VARIABLE_NOT_DEFINED.replace('%s', node.id, 1))
            node.computed_type = ErrorType()
        
    @visitor.when(ComplementNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        if IsAuto(node.expr.computed_type.name):
            self.update(node.expr, scope, self.context.get_type('Int'))
            node.computed_type = node.expr.computed_type
        else:
            if node.expr.computed_type.name != 'Int':
                self.errors.append("Complement works only for Int")
                node.computed_type = ErrorType()
            else:
                node.computed_type = self.context.get_type('Int')

    @visitor.when(NotNode)
    def visit(self, node, scope):
        self.visit(node.expr, scope)
        if IsAuto(node.expr.computed_type.name):
            self.update(node.expr, scope, self.context.get_type('Bool'))
            node.computed_type = node.expr.computed_type
        else:
            if node.expr.computed_type.name != 'Bool':
                self.errors.append("Not operator works only for Bool")
                node.computed_type = ErrorType()
            else:
                node.computed_type = self.context.get_type('Bool')
   
    @visitor.when(BinaryNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = node.left.computed_type
        
        self.visit(node.right, scope)
        right_type = node.right.computed_type

        if IsAuto(left_type.name):
        	self.update(node.left, scope, self.context.get_type('Int'))
        	left_type = node.left.computed_type

        if IsAuto(right_type.name):
        	self.update(node.right, scope, self.context.get_type('Int'))
        	right_type = node.right.computed_type
        
        if not (IsAuto(left_type.name) or left_type.conforms_to(IntType())) or not (IsAuto(right_type.name) or right_type.conforms_to(IntType())):
            self.errors.append(INVALID_OPERATION.replace('%s', left_type.name, 1).replace('%s', right_type.name, 1))
            node_type = ErrorType()
        else:
            node_type = IntType()
            
        node.computed_type = node_type
        
    @visitor.when(FunctionCallNode)
    def visit(self, node, scope):
        self.visit(node.obj, scope)
        obj_type = node.obj.computed_type
        
        if node.type:
            try:
                if IsAuto(node.type):
                    raise SemanticError('Is not possible to use AUTO_TYPE in a cast')
                if not obj_type.conforms_to(self.context.get_type(node.type)):
                    self.errors.append(INCOMPATIBLE_TYPES.replace('%s', obj_type.name, 1).replace('%s', node.type, 1))
            except SemanticError as ex:
                self.errors.append(ex.text)
                
        try:
            if node.type:
                obj_method = self.context.get_type(node.type).get_method(node.id)
            else:
                obj_method = obj_type.get_method(node.id)
            
            if len(node.args) == len(obj_method.param_types):
                for idx, arg in enumerate(node.args):
                    self.visit(arg, scope)
                    arg_type = arg.computed_type
                    param_type = obj_method.param_types[idx]
                    
                    if IsAuto(param_type.name):
                    	if not IsAuto(arg_type.name):
                    		obj_method.param_types[idx] = arg_type
                    else:
                    	if IsAuto(arg_type.name):
                    		self.update(arg, scope, param_type)
                    	else:
		                    if not arg_type.conforms_to(param_type):
		                        self.errors.append(INCOMPATIBLE_TYPES.replace('%s', arg_type.name, 1).replace('%s', param_type.name, 1))
            else:
                self.errors.append(f'Method "{obj_method.name}" of "{obj_type.name}" only accepts {len(obj_method.param_types)} argument(s)')
            
            node_type = obj_method.return_type
        except SemanticError as ex:
            self.errors.append(ex.text)
            node_type = ErrorType()
            
        node.computed_type = node_type
    
    @visitor.when(MemberCallNode)
    def visit(self, node, scope):
        obj_type = self.current_type
        
        try:
            obj_method = obj_type.get_method(node.id)
            
            if len(node.args) == len(obj_method.param_types):
                for idx, arg in enumerate(node.args):
                    self.visit(arg, scope)
                    arg_type = arg.computed_type
                    param_type = obj_method.param_types[idx]
                    
                    if IsAuto(param_type.name):
                    	if not IsAuto(arg_type.name):
                    		obj_method.param_types[idx] = arg_type
                    else:
                    	if IsAuto(arg_type.name):
                    		self.update(arg, scope, param_type)
                    	else:
		                    if not arg_type.conforms_to(param_type):
		                        self.errors.append(INCOMPATIBLE_TYPES.replace('%s', arg_type.name, 1).replace('%s', param_type.name, 1))
            else:
                self.errors.append(f'Method "{obj_method.name}" of "{obj_type.name}" only accepts {len(obj_method.param_types)} argument(s)')
            
            node_type = obj_method.return_type
        except SemanticError as ex:
            self.errors.append(ex.text)
            node_type = ErrorType()
            
        node.computed_type = node_type

    @visitor.when(ArithmeticNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = node.left.computed_type
        
        self.visit(node.right, scope)
        right_type = node.right.computed_type

        if IsAuto(left_type.name):
        	self.update(node.left, scope, self.context.get_type('Int'))
        	left_type = node.left.computed_type

        if IsAuto(right_type.name):
        	self.update(node.right, scope, self.context.get_type('Int'))
        	right_type = node.right.computed_type
        
        if not (IsAuto(left_type.name) or left_type.conforms_to(IntType())) or not (IsAuto(right_type.name) or right_type.conforms_to(IntType())):
            self.errors.append(INVALID_OPERATION.replace('%s', left_type.name, 1).replace('%s', right_type.name, 1))
            node_type = ErrorType()
        else:
            node_type = IntType()
            
        node.computed_type = node_type

    @visitor.when(ComparisonNode)
    def visit(self, node, scope):
        self.visit(node.left, scope)
        left_type = node.left.computed_type
        
        self.visit(node.right, scope)
        right_type = node.right.computed_type

        if IsAuto(left_type.name):
        	self.update(node.left, scope, self.context.get_type('Bool'))
        	left_type = node.left.computed_type

        if IsAuto(right_type.name):
        	self.update(node.right, scope, self.context.get_type('Bool'))
        	right_type = node.right.computed_type
        
        if not (match(left_type, BoolType()) and match(right_type, BoolType())):
            self.errors.append(INVALID_OPERATION.replace('%s', left_type.name, 1).replace('%s', right_type.name, 1))
            node_type = ErrorType()
        else:
            node_type = BoolType()
            
        node.computed_type = node_type

    @visitor.when(EqualNode)
    def visit(self, node, scope):
        # //TODO: What to do when left and rigth are AUTO
        self.visit(node.left, scope)
        left_type = node.left.computed_type
        
        self.visit(node.right, scope)
        right_type = node.right.computed_type
        
        if not (left_type.name == right_type.name and left_type.name in built_in_types[:3]):
            self.errors.append(INVALID_OPERATION.replace('%s', left_type.name, 1).replace('%s', right_type.name, 1))
            node_type = ErrorType()
        else:
            node_type = right_type
            
        node.computed_type = node_type

class ComputedVisitor(FormatVisitor):
    def replace_auto(self, name):
        return 'Object' if IsAuto(name) else name

    @visitor.on('node')
    def visit(self, node, tabs):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__ProgramNode [<class> ... <class>]'
        statements = '\n'.join(self.visit(child, tabs + 1) for child in node.declarations)
        return f'{ans}\n{statements}'
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node, tabs=0):
        parent = '' if node.parent is None else f"inherits {node.parent}"
        ans = '\t' * tabs + f'\\__ClassDeclarationNode: class {node.id} {parent} {{ <feature> ... <feature> }}'
        features = '\n'.join(self.visit(child, tabs + 1) for child in node.features)
        return f'{ans}\n{features}'
    
    @visitor.when(AttrDeclarationNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] if node.expr else []
        text = '<- <expr>' if node.expr else ''
        real_type = self.replace_auto(node.scope.find_variable(node.id).type.name)
        ans = '\t' * tabs + f'\\__AttrDeclarationNode: {node.id} : {real_type} {text}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}' if body else f'{ans}'
    
    @visitor.when(FuncDeclarationNode)
    def visit(self, node, tabs=0):
        params = ', '.join(':'.join(param) for param in node.params)
        real_type = self.replace_auto(node.method.return_type.name)
        ans = '\t' * tabs + f'\\__FuncDeclarationNode: {node.id}({params}) : {real_type} {{<body>}}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in node.body)
        return f'{ans}\n{body}'
    
    @visitor.when(IfThenElseNode)
    def visit(self, node, tabs=0):
        sons = [node.condition, node.if_body]
        text = ''
        if node.else_body:
            sons.append(node.else_body)
            text += 'else <body>'
        ans = '\t' * tabs + f'\\__IfThenElseNode: if <cond> then <body> {text} fi'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(WhileLoopNode)
    def visit(self, node, tabs=0):
        sons = [node.condition, node.body]
        ans = '\t' * tabs + f'\\__WhileLoopNode: while <cond> loop <body> pool'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(BlockNode)
    def visit(self, node, tabs=0):
        sons = node.exprs
        ans = '\t' * tabs + f'\\__BlockNode: {{<expr> ... <expr>}}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(LetInNode)
    def visit(self, node, tabs=0):
        sons = node.let_body + [node.in_body]
        ans = '\t' * tabs + f'\\__LetInNode: let {{<attr> ... <attr>}} in <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(CaseOfNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] + node.branches
        ans = '\t' * tabs + f'\\__CaseOfNode: case <expr> of {{<case> ... <case>}} esac'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(CaseExpressionNode)
    def visit(self, node, tabs=0):
        sons = [node.expr]
        ans = '\t' * tabs + f'\\__CaseExpressionNode: {node.id} : {node.type} => <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'

    @visitor.when(LetAttributeNode)
    def visit(self, node, tabs=0):
        sons = [node.expr] if node.expr else []
        text = '<- <expr>' if node.expr else ''
        real_type = self.replace_auto(node.scope.find_variable(node.id).type.name)
        ans = '\t' * tabs + f'\\__LetAttributeNode: {node.id} : {real_type} {text}'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}' if body else f'{ans}'
    
    @visitor.when(AssignNode)
    def visit(self, node, tabs=0):
        sons = [node.expr]
        ans = '\t' * tabs + f'\\__AssignNode: {node.id} <- <expr>'
        body = '\n'.join(self.visit(child, tabs + 1) for child in sons)
        return f'{ans}\n{body}'
    
    @visitor.when(UnaryNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__{node.__class__.__name__} <expr>'
        right = self.visit(node.expr, tabs + 1)
        return f'{ans}\n{right}'
   
    @visitor.when(BinaryNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__<expr> {node.__class__.__name__} <expr>'
        left = self.visit(node.left, tabs + 1)
        right = self.visit(node.right, tabs + 1)
        return f'{ans}\n{left}\n{right}'

    @visitor.when(AtomicNode)
    def visit(self, node, tabs=0):
        return '\t' * tabs + f'\\__ {node.__class__.__name__}: {node.lex}'
    
    @visitor.when(FunctionCallNode)
    def visit(self, node, tabs=0):
        obj = self.visit(node.obj, tabs + 1)
        ans = '\t' * tabs + f'\\__FunctionCallNode: <obj>.{node.id}(<expr>, ..., <expr>)'
        args = '\n'.join(self.visit(arg, tabs + 1) for arg in node.args)
        return f'{ans}\n{obj}\n{args}'

    @visitor.when(MemberCallNode)
    def visit(self, node, tabs=0):
        ans = '\t' * tabs + f'\\__MemberCallNode: {node.id}(<expr>, ..., <expr>)'
        args = '\n'.join(self.visit(arg, tabs + 1) for arg in node.args)
        return f'{ans}\n{args}'
    
    @visitor.when(NewNode)
    def visit(self, node, tabs=0):
        return '\t' * tabs + f'\\__NewNode: new {node.type}()'
