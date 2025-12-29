import sys
from LLVMGenerator import LLVMGenerator
from antlr4 import *
from LexerParser.MyLangParser import MyLangParser
from LexerParser.MyLangVisitor import MyLangVisitor
import numpy as np

"""
[0] = value (literal | pointer | tuple)
[1] = type
"""

class VariableInfo:
    def __init__(self, name, type_info="Undefined"):
        self.name = name
        self.type_info = type_info

    def __str__(self):
        return f"VariableInfo(name={self.name}, type_info={self.type_info})"

    def __repr__(self):
        return self.__str__()

class LLVMActions(MyLangVisitor):
    def __init__(self):
        self.scope_history = []
        
        self.variables = [{}]
        self.label_counter = 0
        self.temp_var_counter = 0
        self.functions = {}
        self.structs = {}
        self.struct_sizes = {}
        self.classes = {}
        self.class_name = None
        self.current_function = None
        self.current_ret_type = 'void'
        self._yield_counter = 0   
        self._current_gen_state = 0     
        self._gen_current_type = None 
        self.gen_elem_type = {}   

    def _register_class(self, cname, llvm_fields, fields_map):
        """Record class meta-data and ask LLVMGenerator to emit the struct."""
        total_size = 8 * len(llvm_fields)       # naive = ptr-sized slots
        self.classes[cname] = dict(
            fields_map=fields_map,              #  name  → (index, type)
            methods_map={},                     #  name  → (ret, [param types])
            size=total_size
        )

    def create_shadow_copy(self, var_name, src, ctx):
        if isinstance(src, VariableInfo):
            src_name   = src.name          
            type_info  = src.type_info
            src_is_reg = False
        else:                                  
            src_name, type_info = src
            src_is_reg = True

        if type_info[1] == "class" and var_name in ("this","self"):
                self.variables[-1][var_name] = VariableInfo(src_name, type_info)
                other = "self" if var_name == "this" else "this"
                self.variables[-1][other] = VariableInfo(src_name, type_info)
                return src_name, type_info

        idx = self.check_if_name_exists(var_name)
        new_var_name = f"@{var_name}" if idx == 0 else f"@{var_name}_{idx}"
            
        if type_info[1] == "class": 
            
            class_name = type_info[0]
            total_size = self.classes[class_name]['size']
            llvm_class_type = f"%class.{class_name}"

            LLVMGenerator.declare_class(new_var_name, class_name)
            class_copy_reg = LLVMGenerator.allocate_class(class_name, total_size)
            LLVMGenerator.store_class(new_var_name, class_name, class_copy_reg)

            dest_reg = LLVMGenerator.bitcast(f"%{class_copy_reg}", llvm_class_type)
            LLVMGenerator.memcpy(f"%{dest_reg}", src_name, total_size, 8, llvm_class_type)


        elif type_info[1] == "struct":
            
            total_size = self.struct_sizes[type_info[0]]
            llvm_struct_type = f"%struct.{type_info[0]}"
                        
            LLVMGenerator.declare_struct(new_var_name, type_info[0])
            reg = LLVMGenerator.initialize_struct(new_var_name, type_info[0], total_size)
            
            # dest_ptr = LLVMGenerator.get_struct_ptr(new_var_name, type_info[0])
            # src_ptr = LLVMGenerator.get_struct_ptr(f"%{var_name}", type_info[0])

            dest_reg = LLVMGenerator.bitcast(f"%{reg}", llvm_struct_type)
            
            LLVMGenerator.memcpy(f"%{dest_reg}", f"%{var_name}", total_size, 8, llvm_struct_type)

        elif isinstance(type_info, tuple):                    
            sizes, etype = type_info
            llvm_el_type = self.getLLVMType(etype)
            llvm_array_type   = self.build_array_sig(type_info) 
            
            LLVMGenerator.declare_array(new_var_name, llvm_el_type, sizes)

            total_elems  = 1
            for s in sizes: total_elems *= int(s)
            
            if etype == 'int':
                element_size = 4
            elif etype == 'float':
                element_size = 4
            elif etype == 'double':
                element_size = 8
            elif etype == 'bool':
                element_size = 1
            elif etype == 'string':
                element_size = 8
            else:
                self.error(ctx.start.line,f"Unrecognized array type")
                
            total_bytes  = total_elems * element_size

            LLVMGenerator.memcpy(new_var_name, src_name, total_bytes, element_size, llvm_array_type)
        else:                                     
            if type_info == "int": LLVMGenerator.declare_int(new_var_name)
            elif type_info == "float": LLVMGenerator.declare_float(new_var_name)
            elif type_info == "double": LLVMGenerator.declare_double(new_var_name)
            elif type_info == "bool": LLVMGenerator.declare_bool(new_var_name)
            elif type_info == "string": LLVMGenerator.declare_string(new_var_name)

            if src_is_reg:
                val = src_name             
            else:
                if type_info == "int":    val = f"%{LLVMGenerator.load_int(src_name)}"
                elif type_info == "float":  val = f"%{LLVMGenerator.load_float(src_name)}"
                elif type_info == "double": val = f"%{LLVMGenerator.load_double(src_name)}"
                elif type_info == "bool":   val = f"%{LLVMGenerator.load_bool(src_name)}"
                elif type_info == "string": val = f"%{LLVMGenerator.load_string(src_name)}"

            if type_info == "int": LLVMGenerator.assign_int(new_var_name, val)
            elif type_info == "float": LLVMGenerator.assign_float(new_var_name, val)
            elif type_info == "double": LLVMGenerator.assign_double(new_var_name, val)
            elif type_info == "bool": LLVMGenerator.assign_bool(new_var_name, val)
            elif type_info == "string": LLVMGenerator.assign_string(new_var_name, val)

        self.variables[-1][var_name] = VariableInfo(new_var_name, type_info)
        return new_var_name, type_info

    def get_data_from_scope(self, var_name, ctx):
        var_name_in_other_scope = next((scope for scope in reversed(self.variables) if var_name in scope), None) 
        if var_name_in_other_scope:
            return var_name_in_other_scope[var_name].name, var_name_in_other_scope[var_name].type_info
        else:
            self.error(ctx.start.line, f"Invalid variable name: {var_name}")

    def get_class_name(self, var_ref: str):
        for scope in reversed(self.variables + self.scope_history):
            for logical_name, info in scope.items():
                if info.name == var_ref or logical_name == var_ref.lstrip('@'):
                    ti = info.type_info
                    if isinstance(ti, tuple) and ti[1] == 'class':
                        return ti[0]

        # 2. kontekst „this” / „self” wewnątrz metody
        if self.class_name:
            return self.class_name

        self.error(-1, f"Nie można ustalić nazwy klasy dla {var_ref}")


    def check_current_scope(self, var_name):
        if var_name in self.variables[-1]:
            return True
        else:
            return False
        
    def check_if_name_exists(self, var_name):
        one = sum(1 for scope in self.variables if var_name in scope)
        two = 0
        
        for scope in self.scope_history:
            if var_name in scope:
                two += 1
        
        return one + two
            
    def getLLVMType(self, type_name):
        if isinstance(type_name, tuple) and type_name[1] == 'generator':
            return f"%{type_name[0]}.gen*"
        mapping = {"int": "i32", "float": "float", "double": "double", "bool": "i1", "string": "i8*"}
        return mapping.get(type_name, type_name)

    def getLLVMDefault(self, type_name):
        mapping = {"int": "0", "float": "0.0", "double": "0.0", "bool": "false", "string": "null"}
        return mapping.get(type_name, type_name)

    def visitProgram(self, ctx: MyLangParser.ProgramContext):
        self.visitChildren(ctx)
        
        print(self.scope_history)
        print(self.variables)
        return LLVMGenerator.generate()

    def visitVarDecl(self, ctx: MyLangParser.VarDeclContext):
        is_static = ctx.static is not None 

        initializer = None
        if ctx.initializer():
            initializer = self.visit(ctx.initializer())

        if ctx.var:
            if initializer is None:
                self.error(ctx.start.line, "Variable declared with 'var' must have an initializer")
            type_info = self.infer_type(initializer)
            if type_info is None:
                self.error(ctx.start.line, "Could not infer type for 'var' variable")
        else:
            type_info = self.visit(ctx.advancedType())

        var_name_og = ctx.ID().getText()
        
        if self.check_current_scope(var_name_og):
            self.error(ctx.start.line, f"Variable name already exists") 
        
        idx = self.check_if_name_exists(var_name_og)
        var_name = f"@{var_name_og}" if idx == 0 else f"@{var_name_og}_{idx}"

        if isinstance(type_info, tuple) and type_info[0] in self.structs:
            LLVMGenerator.declare_struct(var_name, type_info[0])
            if not ctx.initializer():
                self.error(ctx.start.line, f"Struct must be inicialized on declaration")
        elif isinstance(type_info, tuple) and type_info[0] in self.classes:
            LLVMGenerator.declare_class(var_name, type_info[0])
            if isinstance(type_info, tuple) and type_info[1] == 'class' and initializer:
                init_val, init_type = initializer
                total   = self.classes[type_info[0]]['size']
                obj_reg = LLVMGenerator.allocate_class(type_info[0], total)
                LLVMGenerator.store_class(var_name, type_info[0], obj_reg)

                src_reg = LLVMGenerator.get_class_ptr(init_val, type_info[0])
                llvm_cls = f"%class.{type_info[0]}"
                dst_reg  = LLVMGenerator.bitcast(f"%{obj_reg}", llvm_cls)
                LLVMGenerator.memcpy(f"%{dst_reg}", f"%{src_reg}", total, 8, llvm_cls)

                self.variables[-1][var_name_og] = VariableInfo(var_name, type_info)
                return None

            if not ctx.initializer():
                self.error(ctx.start.line, f"Class must be inicialized on declaration")
        elif isinstance(type_info, tuple) and type_info[1] == 'generator':
            LLVMGenerator.header_text.append(
                f"{var_name} = global i8* null")   # tymczasowy placeholder
        elif isinstance(type_info, tuple):
            sizes = type_info[0]
            element_type = type_info[1]
            llvm_element_type = self.getLLVMType(element_type)
            LLVMGenerator.declare_array(var_name, llvm_element_type, sizes)
        elif type_info == "int":
            LLVMGenerator.declare_int(var_name)
        elif type_info == "float":
            LLVMGenerator.declare_float(var_name)
        elif type_info == "double":
            LLVMGenerator.declare_double(var_name)
        elif type_info == "string":
            LLVMGenerator.declare_string(var_name)
        elif type_info == "bool":
            LLVMGenerator.declare_bool(var_name)
        else:
            self.error(ctx.start.line, f"Invalid variable type")
        
        self.variables[-1][var_name_og] = VariableInfo(var_name, type_info)

        if initializer is not None:
            
            if isinstance(type_info, tuple) and type_info[1] == 'generator':
                if initializer is None:
                    self.error(ctx.start.line, "Generator variable must be initialised")

                init_val, init_type = initializer
                if not (isinstance(init_type, tuple) and init_type[1] == 'generator'):
                    self.error(ctx.start.line, "Only generator value can be assigned to generator variable")

                gen_name = init_type[0]                        # 'oddNumbers'
                llvm_t   = self.getLLVMType(init_type)         # %oddNumbers.gen*

                # popraw global-deklarację (zamiana i8* na %X.gen*)
                LLVMGenerator.header_text[-1] = f"{var_name} = global {llvm_t} null"
                # store wartości
                LLVMGenerator.buffor_stack[-1].append(
                    f"store {llvm_t} {init_val}, {llvm_t}* {var_name}")

                # zapisz ostateczny typ w tablicy zmiennych
                self.variables[-1][var_name_og].type_info = init_type
                return None
            
            elif isinstance(initializer, tuple):
                literal_value, literal_type = initializer[0], initializer[1]
                self.handle_assignment(ctx, var_name, type_info, literal_value, literal_type)
            else:
                valid, incoming_data_list = self.check_type(initializer, type_info[1] if isinstance(type_info, tuple) else type_info)
                if not valid:
                    self.error(ctx.start.line, f"Invalid type in array assignment")
                # TODO czy zgadza sie rozmiar zmiennej i danych ##TODO sprawdzić czy to TODO ma sens
                reference_list_of_lists = self.generate_combinations(list(type_info[0]))
                
                for (reference_list, value_to_assign) in zip(reference_list_of_lists, incoming_data_list):
                    llvm_element_type = self.getLLVMType(type_info[1] if isinstance(type_info, tuple) else type_info)
                    LLVMGenerator.store_array_element(var_name, list(reference_list), value_to_assign, llvm_element_type, type_info[0] if isinstance(type_info, tuple) else ())
        

        
        return None


    def infer_type(self, data):
        if isinstance(data, list):
            if not data:
                return None  # Empty array cannot infer type

            element_types = []
            for element in data:
                elem_type = self.infer_type(element)
                if elem_type is None:
                    return None
                element_types.append(elem_type)

            first_type = element_types[0]
            for t in element_types[1:]:
                if t != first_type:
                    return None  # Inconsistent element types

            dimensions = [len(data)]
            if isinstance(first_type, tuple):
                dimensions += list(first_type[0])
                element_type = first_type[1]
            else:
                element_type = first_type

            return (tuple(dimensions), element_type)
        elif isinstance(data, tuple):
            return data[1]  # Return type of literal
        else:
            return None

    def generate_combinations(self, limits, prefix=[]):
        if not limits:
            return [prefix]
        
        result = []
        for i in range(int(limits[0])):
            new_prefix = prefix + [i]
            result.extend(self.generate_combinations(limits[1:], new_prefix))
            
        return result
    
    def generate_combinations_from_lists(self, lists, prefix=[]):
        if not lists:
            return [prefix]
        result = []
        first_list = lists[0]
        for item in first_list:
            result.extend(self.generate_combinations_from_lists(lists[1:], prefix + [item]))
        return result

    def check_type(self, input_list, expected_type):
        flat_list = []
        for element in input_list:
            if isinstance(element, list):
                res = self.check_type(element, expected_type)
                if res is False:
                    return False
                # Rozpakowujemy wynik i dodajemy do listy
                flat_list.extend(res[1])
            else:
                # Zakładamy, że element jest krotką (wartość, typ)
                if element[1] != expected_type:
                    return False
                flat_list.append(element[0])
        return True, flat_list

    def visitInitializer(self, ctx):
        if ctx.expr():
            return self.visit(ctx.expr())
        elif ctx.arrayInitializer:
            return self.visit(ctx.arrayInitializer())
            
    def handle_assignment(self, ctx, var_name, var_type, to_assign_value, to_assign_type):
        if isinstance(var_type, tuple):
            if var_type[1] == "struct":
                if not to_assign_type:
                    member_list = self.structs[var_type[0]]
                    init = []
                    for member in member_list:
                        init.append(f"{self.getLLVMType(member[1])} {self.getLLVMDefault(member[1])}")

                    total_size = self.struct_sizes[var_type[0]]
                    
                    if var_type[0] != to_assign_value:
                        self.error(ctx.start.line,f"Struct type missmatch")
                    
                    LLVMGenerator.initialize_struct(var_name, var_type[0], total_size)
                    return None

                elif to_assign_type[1] == "struct":
                    if not var_type == to_assign_type:
                        self.error(ctx.start.line,f"Struct type missmatch")
                        
                    total_size = self.struct_sizes[var_type[0]]
                    llvm_struct_type = f"%struct.{var_type[0]}"
                    
                    lhs = LLVMGenerator.get_struct_ptr(var_name, var_type[0])
                    dst_reg = LLVMGenerator.bitcast(f"%{lhs}", llvm_struct_type)
                    
                    LLVMGenerator.memcpy(f"%{dst_reg}", to_assign_value, total_size, 8, llvm_struct_type)
                    
                    return None
                
            # elif var_type[1] == "class":
            #     if not (isinstance(to_assign_type, tuple) and to_assign_type[1] == "class"):
            #         self.error(ctx.start.line,f"Cannot assign non-class value to variable of class '{var_type[0]}'")

            #     if var_type != to_assign_type:
            #         self.error(ctx.start.line,f"Class type missmatch {var_type[0]} vs {to_assign_type[0]}")
                    
            #     total_size = self.classes[var_type[0]]['size']
            #     llvm_class_type = f"%class.{var_type[0]}"
                
            #     lhs = LLVMGenerator.get_class_ptr(var_name, var_type[0])
            #     dst_reg = LLVMGenerator.bitcast(f"%{lhs}", llvm_class_type)
                
            #     LLVMGenerator.memcpy(f"%{dst_reg}", to_assign_value, total_size, 8, llvm_class_type)

            #     return None
                    
            elif var_type[1] == "class":
                # 1. kontrola typów
                if not (isinstance(to_assign_type, tuple) and to_assign_type[1] == "class"):
                    self.error(ctx.start.line, "Cannot assign non-class value to class variable")
                if var_type[0] != to_assign_type[0]:
                    self.error(ctx.start.line, "Class type mismatch")

                total   = self.classes[var_type[0]]['size']
                obj_reg = LLVMGenerator.allocate_class(var_type[0], total)
                LLVMGenerator.store_class(var_name, var_type[0], obj_reg)

                # 3. deep-copy: ładujemy *prawdziwy* adres RHS
                src_reg = LLVMGenerator.get_class_ptr(to_assign_value, var_type[0])

                llvm_cls = f"%class.{var_type[0]}"
                dst_reg  = LLVMGenerator.bitcast(f"%{obj_reg}", llvm_cls)
                LLVMGenerator.memcpy(f"%{dst_reg}", f"%{src_reg}", total, 8, llvm_cls)
                return None
                                
            if not isinstance(to_assign_type, tuple):
                self.error(ctx.start.line,f"Invalid assign to type array")
            if (var_type[0]!=to_assign_type[0]):
                self.error(ctx.start.line,f"Array sizes missmatch")
            if (var_type[1]!=to_assign_type[1]):
                self.error(ctx.start.line,f"Array type missmatch")
                
            total_elements = 1
            for dim in var_type[0]:
                total_elements *= int(dim)
            if var_type[1] == 'int':
                element_size = 4
            elif var_type[1] == 'float':
                element_size = 4
            elif var_type[1] == 'double':
                element_size = 8
            elif var_type[1] == 'bool':
                element_size = 1
            elif var_type[1] == 'string':
                element_size = 8
            else:
                self.error(ctx.start.line,f"Unrecognized array type")
            
            total_size = total_elements * element_size
            llvm_element_type = self.getLLVMType(to_assign_type[1])
            LLVMGenerator.memcpy(var_name, to_assign_value, total_size, element_size, llvm_element_type)
            return
                
        elif var_type == "int":
            if to_assign_type == "int":
                LLVMGenerator.assign_int(var_name, to_assign_value)
            else:
                self.error(
                    ctx.start.line,
                    f"Invalid type '{to_assign_type}':'{to_assign_value}' assigned to variable '{var_name}' of type '{var_type}'"
                )
        
        elif var_type == "float":
            if to_assign_type == "float":
                LLVMGenerator.assign_float(var_name, to_assign_value)
            elif to_assign_type == "int":
                float_version = float(to_assign_value)
                LLVMGenerator.assign_float(var_name, float_version)
            else:
                self.error(
                    ctx.start.line,
                    f"Invalid type '{to_assign_type}':'{to_assign_value}' assigned to variable '{var_name}' of type '{var_type}'"
                )
        
        elif var_type == "double":
            if to_assign_type in ("double", "float"):
                LLVMGenerator.assign_double(var_name, to_assign_value)
            elif to_assign_type == "int":
                float_version = float(to_assign_value)
                LLVMGenerator.assign_double(var_name, float_version)
            else:
                self.error(
                    ctx.start.line,
                    f"Invalid type '{to_assign_type}':'{to_assign_value}' assigned to variable '{var_name}' of type '{var_type}'"
                )
        
        elif var_type == "string":
            if to_assign_type == "string":
                LLVMGenerator.assign_string(var_name, to_assign_value)
            else:
                self.error(
                    ctx.start.line,
                    f"Invalid type '{to_assign_type}':'{to_assign_value}' assigned to variable '{var_name}' of type '{var_type}'"
                )
        
        elif var_type == "bool":
            if to_assign_type == "bool":
                LLVMGenerator.assign_bool(var_name, to_assign_value)
            else:
                self.error(ctx.start.line, f"Invalid type '{to_assign_type}' assigned to variable '{var_name}' of type '{var_type}'")         
        
        elif var_type in self.structs:
            self.error(ctx.start.line, f"Handle struct assignment")
        else:
            self.error(
                ctx.start.line,
                f"Unsupported variable type"
            )

    def visitAssignable(self, ctx):
        name = ctx.ID().getText()
        
        if ctx.references():
            reference = self.visit(ctx.references())
        else:
            reference = None

        return (name, reference)
    
    def visitReferences(self, ctx: MyLangParser.ReferenceContext):
        indices = []
        for index in ctx.getChildren():
            indices.append(self.visit(index))
        return tuple(indices)
    
    def visitReference(self, ctx: MyLangParser.ReferenceContext):
        if ctx.indexing():
            indexing = self.visit(ctx.indexing())
            return indexing     
        else: 
            return ctx.ID().getText()

    def visitIndexing(self, ctx: MyLangParser.IndexingContext):
        if ctx.index():
            return self.visit(ctx.index())
        else:
            return self.visit(ctx.indexRange())
        
    def visitIndexRange(self, ctx):
        if ctx.leftExpr:
            firstExpr = self.visit(ctx.leftExpr)
            if firstExpr[1] != 'int':
                self.error(
                    ctx.start.line,
                    f"Invalid type of range index '{firstExpr[1]}'"
                )
        else:
            firstExpr = (None,)
        if ctx.rightExpr:
            secondExpr = self.visit(ctx.rightExpr)
            if secondExpr[1] != 'int':
                self.error(
                    ctx.start.line,
                    f"Invalid type of range index '{secondExpr[1]}'"
                )
        else:
            secondExpr = (None,)
        return (firstExpr[0],':',secondExpr[0])
        
    def visitIndex(self, ctx: MyLangParser.IndexContext):
        expr = self.visit(ctx.expr())
        if not expr or expr[1] != 'int':
            self.error(ctx.start.line, f"Invalid index value '{expr[1]}'") 
        return expr[0]
    
    def compute_initializer_shape(self, data):
        if isinstance(data, list):
            if not data:
                return [0]
            return [len(data)] + self.compute_initializer_shape(data[0])
        return []

    def visitAssignment(self, ctx: MyLangParser.AssignmentContext):
        var_name, references = self.visit(ctx.assignable())
        
        if not self.check_current_scope(var_name):
            print(f"Variable '{var_name}' not found in current scope")
            self.error(ctx.start.line, f"Assignable variable outside of scope") 
        
        var_name, type_info = self.get_data_from_scope(var_name, ctx)
        
        if references is None:
            value_reg, value_type = self.visit(ctx.initializer())
            self.handle_assignment(ctx, var_name, type_info, value_reg, value_type)
            return None

        initializer = self.visit(ctx.initializer())

        if type_info[1] == "struct":
            field_idx = next(i for i,(fname,_) in enumerate(self.structs[type_info[0]]) if fname == references[0])
            field_type = self.structs[type_info[0]][field_idx][1]
            if field_idx is None:
                self.error(ctx.start.line, f"Invalid field name '{references}' for struct '{type_info[0]}'")
            struct_ptr = LLVMGenerator.get_struct_ptr(var_name, type_info[0])
            field_ptr = LLVMGenerator.get_struct_field_ptr(struct_ptr, type_info[0], field_idx)
            if not isinstance(field_type, tuple):
                self.handle_assignment(ctx, field_ptr, field_type, initializer[0], initializer[1])
                return None
            # jesli mamy array po lewej stronie            
            var_name = field_ptr
            type_info = field_type
            references = references[1:]

        if type_info[1] == "class":
            field_name = references[0]
            if field_name not in self.classes[type_info[0]]['fields_map']:
                self.error(ctx.start.line, f"Invalid field name '{field_name}' for class '{type_info[0]}'")
            
            idx, field_type = self.classes[type_info[0]]['fields_map'][field_name]

            obj_ptr = LLVMGenerator.get_class_ptr(var_name, type_info[0])
            field_ptr = LLVMGenerator.get_class_field_ptr(f"%{obj_ptr}", type_info[0], idx)
            
            if not isinstance(field_type, tuple):
                self.handle_assignment(ctx, f"%{field_ptr}", field_type, initializer[0], initializer[1])
                return None
            
            # jesli mamy array po lewej stronie 
            var_name = field_ptr
            type_info = field_type
            references = references[1:]           

        sizes = type_info[0]
        element_type = type_info[1]
        llvm_element_type = self.getLLVMType(element_type)

        if isinstance(initializer, tuple):
            value_reg, value_type = initializer[0], initializer[1]
            if any(isinstance(idx, tuple) for idx in references):
                full_references = []
                if len(references) != len(sizes):
                    for _ in range(len(sizes) - len(references)):
                        references = references + ((None, ":", None),)
                for idx, size in zip(references, sizes):
                    if isinstance(idx, tuple) and len(idx) == 3 and idx[1] == ':':
                        lower, _, upper = idx
                        lower = 0 if lower is None else lower
                        upper = int(size) if upper is None else upper
                        
                        if upper > int(size):
                            self.error(ctx.start.line, f"Array index out of bounds")
                        if not isinstance(lower, int):
                            self.error(ctx.start.line, f"Invalid index type '{lower}'")
                        if not isinstance(upper, int):
                            self.error(ctx.start.line, f"Invalid index type '{upper}'")
                            
                        expanded_references = list(range(lower, upper))
                        full_references.append(expanded_references)
                    else:
                        if not isinstance(idx, int):
                            self.error(ctx.start.line, f"Invalid index type '{idx}'")
                        full_references.append([idx]) # ([1],([1],[2],[3]))
                        
                index_combinations = self.generate_combinations_from_lists(full_references)
                shape = self.compute_output_shape(index_combinations)
                if isinstance(initializer[1], tuple):
                    initializer_shape = [int(dim) for dim in initializer[1][0]]
                else:
                    initializer_shape = [1]

                if shape != initializer_shape:
                    self.error(ctx.start.line, f"Invalid number of values assigned to array")
                
                sizes = type_info[0]
                element_type = type_info[1]
                llvm_element_type = self.getLLVMType(element_type)
                
                src_indices =  self.generate_combinations(initializer_shape)
                initializer_shape = initializer_shape[0] if len(initializer_shape) == 1 else tuple(initializer_shape)
                
                for dst_idx, src_idx in zip(index_combinations, src_indices):
                    src_ptr = LLVMGenerator.get_array_element_ptr(value_reg, src_idx, llvm_element_type, initializer_shape)
                    val = LLVMGenerator.load_array_element(llvm_element_type, src_ptr)
                    LLVMGenerator.store_array_element(var_name, dst_idx, f"%{val}", llvm_element_type, sizes)
                return None
            else:
                sizes = type_info[0]
                element_type = type_info[1]
                if isinstance(initializer[1], tuple):
                    initializer_shape = [int(dim) for dim in initializer[1][0]]
                else:
                    initializer_shape = [1]

                check_size = list(int(x) for x in sizes[len(references):])

                if not check_size:
                    check_size = [1]

                if check_size != initializer_shape:
                    self.error(ctx.start.line, f"Invalid number of values assigned to array")
                    
                llvm_element_type = self.getLLVMType(element_type)
                
                if check_size == [1]:
                    LLVMGenerator.store_array_element(var_name, list(references), value_reg, llvm_element_type, sizes)
                    return None

                ptr = LLVMGenerator.get_array_element_ptr(var_name, list(references), llvm_element_type, sizes)

                total_elems  = 1
                for s in initializer_shape: total_elems *= int(s)
            
                if element_type == 'int':
                    element_size = 4
                elif element_type == 'float':
                    element_size = 4
                elif element_type == 'double':
                    element_size = 8
                elif element_type == 'bool':
                    element_size = 1
                elif element_type == 'string':
                    element_size = 8
                else:
                    self.error(ctx.start.line,f"Unrecognized array type")
                    
                total_bytes  = total_elems * element_size
                    
                llvm_element_type = self.getLLVMType(element_type)
                LLVMGenerator.memcpy(f"%{ptr}", value_reg, total_bytes, element_size, llvm_element_type)
                return None
        else:
            if any(isinstance(idx, tuple) for idx in references):
                full_references = []
                if len(references) != len(sizes):
                    for _ in range(len(sizes) - len(references)):
                        references = references + ((None, ":", None),)
                for idx, size in zip(references, sizes):
                    if isinstance(idx, tuple) and len(idx) == 3 and idx[1] == ':':
                        lower, _, upper = idx
                        lower = 0 if lower is None else lower
                        upper = int(size) if upper is None else upper
                        
                        if upper > int(size):
                            self.error(ctx.start.line, f"Array index out of bounds")
                        if not isinstance(lower, int):
                            self.error(ctx.start.line, f"Invalid index type '{lower}'")
                        if not isinstance(upper, int):
                            self.error(ctx.start.line, f"Invalid index type '{upper}'")
                            
                        expanded_references = list(range(lower, upper))
                        full_references.append(expanded_references)
                    else:
                        if not isinstance(idx, int):
                            self.error(ctx.start.line, f"Invalid index type '{idx}'")
                        full_references.append([idx]) # ([1],([1],[2],[3]))
                        
                index_combinations = self.generate_combinations_from_lists(full_references)
                shape = self.compute_output_shape(index_combinations)
                initializer_shape = self.compute_initializer_shape(initializer)

                if shape != initializer_shape:
                    self.error(ctx.start.line, f"Invalid number of values assigned to array")

                sizes = type_info[0]
                sizes_list = list(sizes)
                element_type = type_info[1]

                valid, values_to_be_assigned = self.check_type(initializer,element_type)
                if not valid:
                    self.error(
                        ctx.start.line,
                        f"Invalid type in array assginement"
                    )

                llvm_element_type = self.getLLVMType(element_type)

                for (reference_list, value_to_assign) in zip(index_combinations, values_to_be_assigned):
                    LLVMGenerator.store_array_element(var_name, list(reference_list), value_to_assign, llvm_element_type, sizes)
                return None
            else:
                sizes = type_info[0]
                element_type = type_info[1]
                
                valid, values_to_be_assigned = self.check_type(initializer,element_type)
                if not valid:
                    self.error(
                        ctx.start.line,
                        f"Invalid type in array assginement"
                    )
                    
                reference_base_list = list(references)
                sizes_list = list(sizes)
                
                reference_list_of_lists =  self.generate_combinations(sizes_list[len(reference_base_list):], reference_base_list)
                llvm_element_type = self.getLLVMType(element_type)
                shape = self.compute_output_shape(reference_list_of_lists)
                initializer_shape = self.compute_initializer_shape(initializer)

                if shape != initializer_shape:
                    self.error(ctx.start.line, f"Invalid number of values assigned to array")
                
                for (reference_list, value_to_assign) in zip(reference_list_of_lists,values_to_be_assigned):
                    LLVMGenerator.store_array_element(var_name, list(reference_list), value_to_assign, llvm_element_type, sizes)
                return None
            
    def visitPrintStmt(self, ctx: MyLangParser.PrintStmtContext):
        reg, value_type = self.visit(ctx.expr())
        if isinstance(value_type, tuple):
            self.error(ctx.start.line, f"Print of variable of array type not supported") 
        if value_type == "int":
            LLVMGenerator.print_int(reg)
        elif value_type == "float":
            LLVMGenerator.print_float(reg)
        elif value_type == "double":
            LLVMGenerator.print_double(reg)
        elif value_type == "string":
            LLVMGenerator.print_string(reg)
        elif value_type == "bool":
            LLVMGenerator.print_bool(reg)
        return None

    def visitReadStmt(self, ctx: MyLangParser.ReadStmtContext):
        var_name = ctx.ID().getText()
        
        if not self.check_current_scope(var_name):
            self.error(ctx.start.line, f"Assignable variable outside of scope") 
        
        var_name, type_info = self.get_data_from_scope(var_name, ctx)
        
        if type_info == "int":
            LLVMGenerator.read_int(var_name)
        elif type_info == "float":
            LLVMGenerator.read_float(var_name)
        elif type_info == "double":
            LLVMGenerator.read_double(var_name)
        elif type_info == "string":
            LLVMGenerator.read_string(var_name)
        return None

    def visitLiteral(self, ctx: MyLangParser.LiteralContext):
        if ctx.INT():
            return (int(ctx.INT().getText()), "int")
        elif ctx.FLOAT():
            text = ctx.FLOAT().getText()
            
            float_value = np.single(text)
            double_value = np.double(text)

            if str(float_value) == str(double_value):
                return (float_value, "float")
            else:
                if str(double_value) != text:
                    self.error(ctx.start.line, f"Assigne value too large for double") 
                else:
                    return (double_value, "double")
        elif ctx.STRING():
            text = ctx.STRING().getText()[1:-1]
            pointer_reg = LLVMGenerator.constant_string(text)
            return (pointer_reg, "string")
        
        elif ctx.BOOL():
            if ctx.BOOL().getText() in ("True", "true"):
                bool_val = 1 
            elif ctx.BOOL().getText() in ("False","false"):
                bool_val = 0
            else:
                self.error(ctx.start.line, f"Invalid value assigned to type bool '{ctx.BOOL().getText()}'") 
            return (bool_val, "bool")
        return (None, None)

    def visitExpr(self, ctx: MyLangParser.ExprContext):
        return self.visitOrExpr(ctx.orExpr())
    

    def visitOrExpr(self, ctx: MyLangParser.OrExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.andExpr())
        
        left_reg, left_type = self.visit(ctx.orExpr())
        if left_type != "bool":
            self.error(ctx.start.line, "LHS of 'or' must be boolean")

        def build_rhs():
            rhs_reg, rhs_type = self.visit(ctx.andExpr())
            if rhs_type != "bool":
                self.error(ctx.start.line, "RHS of 'or' must be boolean")
            return rhs_reg
        
        reg = LLVMGenerator.or_expr(left_reg, build_rhs)

        return (f"%{reg}", "bool")
    
    def visitAndExpr(self, ctx: MyLangParser.AndExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.xorExpr())
        
        left_reg, left_type = self.visit(ctx.andExpr())
        if left_type != "bool":
            self.error(ctx.start.line, "LHS of 'and' must be boolean")
        
        def build_rhs():
            rhs_reg, rhs_type = self.visit(ctx.xorExpr())
            if rhs_type != "bool":
                self.error(ctx.start.line, "RHS of 'and' must be boolean")
            return rhs_reg

        reg = LLVMGenerator.and_expr(left_reg, build_rhs)

        return (f"%{reg}", "bool")
    
    def visitXorExpr(self, ctx: MyLangParser.XorExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.eqExpr())
        
        left_reg, left_type = self.visit(ctx.xorExpr())
        right_reg, right_type = self.visit(ctx.eqExpr())

        reg = LLVMGenerator.xor_expr(left_reg, right_reg)

        return (f"%{reg}", "bool")

    def visitEqExpr(self, ctx: MyLangParser.EqExprContext):
        if ctx.getChildCount() == 1:
                return self.visit(ctx.relExpr())
            
        left_reg, left_type = self.visit(ctx.eqExpr())
        right_reg, right_type = self.visit(ctx.relExpr())
            
        if left_type == "string" and right_type == "string":
            # Generate strcmp call
            strcmp_reg = LLVMGenerator.strcmp_call(left_reg, right_reg)
            
            # Compare strcmp result to 0 (equality)
            op = ctx.equals or ctx.notEquals
            op_type = op.text
            icmp_cond = "eq" if op_type == "==" else "ne"
            cmp_reg = LLVMGenerator.eq_expr_int(icmp_cond, f"%{strcmp_reg}", "0", "i32")
            return (f"%{cmp_reg}", "bool")
        
        casted_left, casted_right, result_type = self.cast_types(left_reg, left_type, right_reg, right_type)
        llvm_type = self.getLLVMType(result_type)
        
        op = ctx.equals or ctx.notEquals
        op_type = op.text
        
        if result_type in ('int', 'bool'):
            icmp_cond = 'eq' if op_type == '==' else 'ne'
            cmp_reg = LLVMGenerator.eq_expr_int(icmp_cond, casted_left, casted_right, llvm_type)
        elif result_type in ('float', 'double'):
            fcmp_cond = 'oeq' if op_type == '==' else 'une'
            cmp_reg = LLVMGenerator.eq_expr_f_db(fcmp_cond, casted_left, casted_right, llvm_type)
        else:
            self.error(ctx.start.line, f"Unsupported comparison for type {result_type}")
        
        return (f"%{cmp_reg}", "bool")



    def visitRelExpr(self, ctx: MyLangParser.RelExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.addExpr())
        
        left_reg, left_type = self.visit(ctx.relExpr())
        right_reg, right_type = self.visit(ctx.addExpr())
        
        if left_type == "string" or right_type == "string":
            self.error(ctx.start.line, "Relational operators (>, <, etc.) are not supported for strings")

        casted_left, casted_right, result_type = self.cast_types(left_reg, left_type, right_reg, right_type)
        llvm_type = self.getLLVMType(result_type)
        
        op = ctx.less or ctx.more or ctx.lessEqual or ctx.moreEqual
        op_type = op.text
        
        if result_type in ('int', 'bool'):
            cond_map = {'<': 'slt', '>': 'sgt', '<=': 'sle', '>=': 'sge'}
            icmp_cond = cond_map[op_type]
            cmp_reg = LLVMGenerator.eq_expr_int(icmp_cond, casted_left, casted_right, llvm_type)
        elif result_type in ('float', 'double'):
            cond_map = {'<': 'olt', '>': 'ogt', '<=': 'ole', '>=': 'oge'}
            fcmp_cond = cond_map[op_type]
            cmp_reg = LLVMGenerator.eq_expr_f_db(fcmp_cond, casted_left, casted_right, llvm_type)
        else:
            self.error(ctx.start.line, f"Unsupported comparison for type {result_type}")
        
        return (f"%{cmp_reg}", "bool")


    def cast_types(self, left_reg, left_type, right_reg, right_type):
        type_hierarchy = {'bool': 0, 'int': 1, 'float': 2, 'double': 3}
        left_rank = type_hierarchy[left_type]
        right_rank = type_hierarchy[right_type]
        
        if left_rank == right_rank:
            return left_reg, right_reg, left_type
        
        target_type = left_type if left_rank > right_rank else right_type
        casted_left = self.cast_value(left_reg, left_type, target_type)
        casted_right = self.cast_value(right_reg, right_type, target_type)
        return casted_left, casted_right, target_type

    def cast_value(self, reg, from_type, to_type):
        llvm_from = self.getLLVMType(from_type)
        llvm_to = self.getLLVMType(to_type)
        if from_type == to_type:
            return reg
        
        if from_type == 'int' and to_type == 'float':
            cast_reg = LLVMGenerator.int_to_float(reg)
        elif from_type == 'int' and to_type == 'double':
            cast_reg = LLVMGenerator.int_to_double(reg)
        elif from_type == 'float' and to_type == 'double':
            cast_reg = LLVMGenerator.float_to_double(reg)
        
        return f"%{cast_reg}"

    def perform_operation(self, left_type, left_reg, right_type, right_reg, operation):
        if left_type == "int":
                if right_type == "int":
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_int")
                    result_reg = method(left_reg, right_reg)
                    return (f"%{result_reg}", "int")
                elif right_type == "float":
                    float_reg = LLVMGenerator.int_to_float(left_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_float")
                    result_reg = method(f"%{float_reg}", right_reg)
                    return (f"%{result_reg}", "float")
                elif right_type == "double":
                    double_reg = LLVMGenerator.int_to_double(left_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_double")
                    result_reg = method(f"%{double_reg}", right_reg)
                    return (f"%{result_reg}", "double")
                elif right_type == "string":
                    raise Exception(f"Not implemented yet: {left_type} and {right_type}")
        elif left_type == "float":
                if right_type == "int":
                    float_reg = LLVMGenerator.int_to_float(right_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_float")
                    result_reg = method(left_reg, f"%{float_reg}")
                    return (f"%{result_reg}", "float")
                elif right_type == "float":
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_float")
                    result_reg = method(left_reg, right_reg)
                    return (f"%{result_reg}", "float")
                elif right_type == "double":
                    double_reg = LLVMGenerator.float_to_double(left_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_double")
                    result_reg = method(f"%{double_reg}", right_reg)
                    return (f"%{result_reg}", "double")
                elif right_type == "string":
                        raise Exception(f"Not implemented yet: {left_type} and {right_type}")
        elif left_type == "double":
                if right_type == "int":
                    double_reg = LLVMGenerator.int_to_double(right_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_double")
                    result_reg = method(left_reg, f"%{double_reg}")
                    return (f"%{result_reg}", "double")
                elif right_type == "float":
                    double_reg = LLVMGenerator.float_to_double(right_reg)
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_double")
                    result_reg = method(left_reg, f"%{double_reg}")
                    return (f"%{result_reg}", "double")
                elif right_type == "double":
                    method = getattr(LLVMGenerator, f"{self.operations[operation]}_double")
                    result_reg = method(left_reg, right_reg)
                    return (f"%{result_reg}", "double")
                elif right_type == "string":
                        raise Exception(f"Not implemented yet: {left_type} and {right_type}")
        elif left_type == "string":
            raise Exception(f"Not implemented yet: {left_type} and {right_type}")

    operations = {
        "+" : "add",
        "-" : "sub",
        "/" : "div",
        "*" : "mul"
    }   

    def visitAddExpr(self, ctx: MyLangParser.AddExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.mulExpr())
        
        left_reg, left_type = self.visit(ctx.addExpr())
        right_reg, right_type = self.visit(ctx.mulExpr())

        if ctx.add is not None:
            op_token = ctx.add
        elif ctx.sub is not None:
            op_token = ctx.sub
        else:
            self.error(ctx.start.line, "Missing operator")
        op_type = op_token.text

        return self.perform_operation(left_type, left_reg, right_type, right_reg, op_type)
    
    def visitMulExpr(self, ctx: MyLangParser.MulExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.unaryExpr())
        
        left_reg, left_type = self.visit(ctx.mulExpr())
        right_reg, right_type = self.visit(ctx.unaryExpr())

        if ctx.multiply is not None:
            op_token = ctx.multiply
        elif ctx.divide is not None:
            op_token = ctx.divide
        else:
            self.error(ctx.start.line, "Missing operator")
        op_type = op_token.text

        return self.perform_operation(left_type, left_reg, right_type, right_reg, op_type)
    
    def visitUnaryExpr(self, ctx: MyLangParser.UnaryExprContext):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.primaryExpr())
        
        expr_reg, expr_type = self.visit(ctx.unaryExpr())

        reg = LLVMGenerator.neg_expr(expr_reg)

        return (f"%{reg}", "bool")

    def compute_output_shape(self, index_combinations):
        if not index_combinations:
            return ()

        num_dims = len(index_combinations[0])
        shape = []
        
        for dim in range(num_dims):
            # Collect unique indices for this dimension
            unique_values = {combo[dim] for combo in index_combinations}
            # Only include this dimension if it was actually sliced (more than one unique index)
            if len(unique_values) != 1:
                shape.append(len(unique_values))
        # if only one index is in range       
        if not shape:
            shape = [len(index_combinations)]
        return shape
    
    def compute_destination_indices(self, index_combination, all_index_combinations):
            dest_indices = []
            num_dims = len(index_combination)
            for dim in range(num_dims):
                # Compute the sorted set of unique indices for this dimension across all combinations
                unique_values = sorted({combo[dim] for combo in all_index_combinations})
                # Only include this dimension if it was actually sliced (more than one unique index)
                if len(unique_values) != 1:
                    # The destination index is the rank of the actual index in the sorted list
                    dest_index = unique_values.index(index_combination[dim])
                    dest_indices.append(dest_index)
            return dest_indices

    def visitObjectReference(self, ctx: MyLangParser.ObjectReferenceContext):
        var_name = ctx.ID().getText()
        
        var_name, type_info = self.get_data_from_scope(var_name, ctx)
        
        if isinstance(type_info, tuple) and type_info[1] == 'generator':
            if not ctx.references():
                return (var_name, type_info)

            token = self.visit(ctx.references())[0]
            gen_name = type_info[0]

            # ► potrzebujemy wskaźnik na strukturę generatora
            if var_name.startswith('@'):
                load_reg = LLVMGenerator.get_gen_ptr(var_name, gen_name)
                obj_ptr  = f"%{load_reg}"
            else:
                obj_ptr  = var_name          # już %oddNumbers.gen*

            if token == 'current':
                # 1. jakiego typu elementy yield-uje ten generator?
                elem_t   = self.gen_elem_type.get(gen_name, 'int')   # domyślnie int
                elem_llvm= self.getLLVMType(elem_t)

                load_reg = LLVMGenerator.get_gen_current(obj_ptr, gen_name, elem_llvm)
                return (f"%{load_reg}", elem_t)

            elif token == 'next':
                # zwracamy „funkcję” .next, odwrotnie niż dla pól .current
                return (f"@{gen_name}_next", 'bool', var_name)

            else:
                self.error(ctx.start.line, f"Generator nie ma składowej '{token}'")
        
        is_struct = False
        if type_info[1] == "class":
            is_field = False
            if not ctx.references():
                return (var_name, type_info)
            token = self.visit(ctx.references())[0]

            # field
            if token in self.classes[type_info[0]]['fields_map']:
                idx, f_type = self.classes[type_info[0]]['fields_map'][token]
                
                obj_ptr = LLVMGenerator.get_class_ptr(var_name, type_info[0])
                ptr_reg = LLVMGenerator.get_class_field_ptr(f"%{obj_ptr}", type_info[0], idx)
                
                # ptr_reg = LLVMGenerator.get_class_field_ptr(var_name, type_info[0], idx)
                
                ptr_reg = f"%{ptr_reg}"
                # return (ptr_reg, f_type)
                is_field = True
            
            # method
            elif token in self.classes[type_info[0]]['methods_map']:
                ret_t, _ = self.classes[type_info[0]]['methods_map'][token]
                return (f"@{type_info[0]}_{token}", ret_t, var_name)
            else:
                self.error(ctx.start.line, f"'{token}' is not a member of class '{type_info[0]}'")

            if is_field:
                var_name, type_info = ptr_reg, f_type

        elif type_info[1] == 'struct':
            if ctx.references():
                references = self.visit(ctx.references())
                
                field_idx = next(i for i,(fname,_) in enumerate(self.structs[type_info[0]]) if fname == references[0])
                field_type = self.structs[type_info[0]][field_idx][1]
                
                if field_idx is None:
                    self.error(ctx.start.line, f"Invalid field name '{references}' for struct '{type_info[0]}'")
        
                struct_ptr = LLVMGenerator.get_struct_ptr(var_name, type_info[0])
                field_ptr = LLVMGenerator.get_struct_field_ptr(struct_ptr, type_info[0], field_idx)
                
                is_struct = True
                
                var_name, type_info = field_ptr, field_type
            else:
                reg = LLVMGenerator.get_struct_ptr(var_name, type_info[0])
                return (f"%{reg}", type_info)
        
        if isinstance(type_info, tuple):
            sizes = type_info[0]
            element_type = type_info[1]
            llvm_element_type = self.getLLVMType(element_type)

            if ctx.references():
                indices = self.visit(ctx.references())
                if is_struct:
                    indices = indices[1:]
            else:
                indices = tuple((None, ':', None) for _ in range(len(sizes)))

            if any(isinstance(idx, tuple) for idx in indices):
                full_indices = []
                if len(indices) != len(sizes):
                    for _ in range(len(sizes) - len(indices)):
                        indices = indices + ((None, ":", None),)
                for idx, size in zip(indices, sizes):
                    if isinstance(idx, tuple) and len(idx) == 3 and idx[1] == ':':
                        lower, _, upper = idx
                        lower = 0 if lower is None else lower
                        upper = int(size) if upper is None else upper
                        
                        if upper > int(size):
                            self.error(ctx.start.line, f"Array index out of bounds")
                        if not isinstance(lower, int):
                            self.error(ctx.start.line, f"Invalid index type '{lower}'")
                        if not isinstance(upper, int):
                            self.error(ctx.start.line, f"Invalid index type '{upper}'")
                            
                        expanded_indices = list(range(lower, upper))
                        full_indices.append(expanded_indices)
                    else:
                        if not isinstance(idx, int):
                            self.error(ctx.start.line, f"Invalid index type '{idx}'")
                        full_indices.append([idx]) # ([1],([1],[2],[3]))
                        
                index_combinations = self.generate_combinations_from_lists(full_indices)
                shape = self.compute_output_shape(index_combinations)
                
                temp_reg = f"@_{self.temp_var_counter}_temp"
                self.temp_var_counter += 1
                LLVMGenerator.declare_array(temp_reg, llvm_element_type, tuple(shape))
                for index_combination in index_combinations:
                    ptr = LLVMGenerator.get_array_element_ptr(var_name, index_combination, llvm_element_type, sizes)
                    reg = LLVMGenerator.load_array_element(llvm_element_type, ptr)
                    dest_indices = self.compute_destination_indices(index_combination, index_combinations)
                    LLVMGenerator.store_array_element(temp_reg, dest_indices, f"%{reg}", llvm_element_type, tuple(shape))
                type_info = (tuple(map(str, shape)), element_type)
                reg = temp_reg
            else:
                target_size = sizes[0+len(indices):]
                if target_size:
                    type_info = (target_size, element_type)  #przekazywanie rozmiaru tablicy do ktorej jest ten pointer
                    reg = LLVMGenerator.get_array_element_ptr(var_name, list(indices), llvm_element_type, sizes)
                    
                else:
                    type_info = element_type 
                    reg = LLVMGenerator.get_array_element_ptr(var_name, list(indices), llvm_element_type, sizes)
                    reg = LLVMGenerator.load_array_element(llvm_element_type,reg)
                reg = f"%{reg}"
        
        elif type_info == "func":
            reg = var_name
            type_info = self.functions.get(var_name[1:], {}).get('ret', 'void')
        elif type_info == "int":
            reg = LLVMGenerator.load_int(var_name)
            reg = f"%{reg}"
        elif type_info == "float":
            reg = LLVMGenerator.load_float(var_name)
            reg = f"%{reg}"
        elif type_info == "double":
            reg = LLVMGenerator.load_double(var_name)
            reg = f"%{reg}"
        elif type_info == "string":
            reg = LLVMGenerator.load_string(var_name)
            reg = f"%{reg}"
        elif type_info == "bool":
            reg = LLVMGenerator.load_bool(var_name)
            reg = f"%{reg}"
        
        return (reg, type_info)

    def visitAdvancedType(self, ctx: MyLangParser.AdvancedTypeContext):
        if ctx.primitiveType():
            return self.visit(ctx.primitiveType())
        elif ctx.multiArrayType():
            return self.visit(ctx.multiArrayType())
        elif ctx.generatorType():
            elem_t = self.visit(ctx.generatorType().primitiveType())
            # zwracamy tylko znacznik – prawdziwy typ poznamy z inicjalizatora
            return ('_placeholder', 'generator', elem_t)
        elif ctx.ID():
            if ctx.ID().getText() in self.structs:
                return (ctx.ID().getText(), 'struct')
            elif ctx.ID().getText() in self.classes:
                return (ctx.ID().getText(), 'class')
        else:
            return {}

    def visitNewObjectExpr(self, ctx):
        ref_name = ctx.ID().getText()
        if ref_name not in self.classes and ref_name not in self.structs:
            self.error(ctx.start.line, f"'{ref_name}' not found")
        elif ref_name in self.classes:
            obj_ptr_reg = LLVMGenerator.allocate_class(ref_name, self.classes[ref_name]['size'])
            
            if ctx.argumentList():
                args = self.visit(ctx.argumentList())
                # prepend hidden 'this'
                arg_sig_parts = [f"%class.{ref_name}* %{obj_ptr_reg}"]
                for aval, atype in args:
                    llvm_t = (
                        f"%struct.{atype[0]}*" if isinstance(atype, tuple) and atype[1] == 'struct'
                        else self.build_array_sig(atype) + '*' if isinstance(atype, tuple)
                        else self.getLLVMType(atype)
                    )
                    arg_sig_parts.append(f"{llvm_t} {aval}")

                LLVMGenerator.call_void_function("void",
                    f"@{ref_name}_ctor",
                    ", ".join(arg_sig_parts))
              
            return (f"%{obj_ptr_reg}", (ref_name, "class"))
        
        else:
            ref_name = ctx.ID().getText()
            arg_list = []
            return (ref_name, arg_list)

        
    def visitPrimaryExpr(self, ctx: MyLangParser.PrimaryExprContext):
        if ctx.literal():
            return self.visit(ctx.literal())
        elif ctx.objectReference():
            return self.visit(ctx.objectReference())
        elif ctx.newObjectExpr():
            return self.visit(ctx.newObjectExpr())
        elif ctx.funcCall():
            return self.visit(ctx.funcCall())
        elif ctx.expr():                    
            return self.visit(ctx.expr())   
        else:
            self.error(ctx.start.line, f"Invalid expr")

    def visitMultiArrayType(self, ctx: MyLangParser.MultiArrayTypeContext):
        element_type = self.visit(ctx.primitiveType())
        size = self.visit(ctx.dimensions()) 
        return (size, element_type)
    
    def visitArrayInitializer(self, ctx: MyLangParser.ArrayInitializerContext):
        values = []
        for child in ctx.getChildren():
            if isinstance(child, MyLangParser.ArrayElementContext):
                values.append(self.visit(child))
        return values

    def visitArrayElement(self, ctx: MyLangParser.ArrayElementContext):
        if ctx.expr():
            return self.visit(ctx.expr())
        elif ctx.arrayInitializer():
            return self.visit(ctx.arrayInitializer())
        else:
            self.error(-1,"Not yet implemented 'ArrayElement'")
       
    def visitDimensions(self, ctx: MyLangParser.DimensionsContext):
        size = []
        for dimension in ctx.getChildren():
            size.append(self.visit(dimension))
        return tuple(size)
    
    def visitDimension(self, ctx: MyLangParser.DimensionContext):
        return ctx.getText()[1:-1]
        
    def visitPrimitiveType(self, ctx: MyLangParser.PrimitiveTypeContext):
        return ctx.getText()

    def error(self, line,  msg):
       print(f"Error, line {line}, {msg}")
       sys.exit(1)

    def visitIfStmt(self, ctx: MyLangParser.IfStmtContext):
        cond_reg, cond_type = self.visit(ctx.expr())
        if cond_type != 'bool':
            self.error(ctx.start.line, f"Condition must be boolean, got {cond_type}")

        # Create unique labels for true, false, and merge points.
        true_label = self.new_label()
        false_label = self.new_label() if ctx.else_ is not None else None
        merge_label = self.new_label()

        if false_label:
            LLVMGenerator.if_statement(cond_reg, true_label, false_label)
        else:
            LLVMGenerator.if_statement(cond_reg, true_label, merge_label)

        # True branch
        LLVMGenerator.define_label(true_label)
        self.visit(ctx.block(0))
        LLVMGenerator.jump_label(merge_label)

        # Else branch, if present
        if false_label:
            LLVMGenerator.define_label(false_label)
            self.visit(ctx.block(1))
            LLVMGenerator.jump_label(merge_label)

        # Merge label: continue with the code
        LLVMGenerator.define_label(merge_label)
        return None

    def visitSimpleFor(self, ctx: MyLangParser.SimpleForContext):
        # Handle initialization
        if ctx.decl_vardeclLabel:
            self.visit(ctx.decl_vardeclLabel)
        elif ctx.decl_assignmentLabel:
            self.visit(ctx.decl_assignmentLabel)

        # Generate loop labels
        loop_id = self.label_counter
        cond_label = f"for_cond_{loop_id}"
        body_label = f"for_body_{loop_id}"
        exit_label = f"for_exit_{loop_id}"
        self.label_counter += 3

        LLVMGenerator.jump_label(cond_label)

        # Condition block
        LLVMGenerator.define_label(cond_label)
        if ctx.conditionLabel:
            cond_reg, cond_type = self.visit(ctx.conditionLabel)
            if cond_type != "bool":
                self.error(ctx.start.line, "Condition must be boolean")
            LLVMGenerator.if_statement(cond_reg, body_label, exit_label)
        else:
            # Infinite loop if no condition
            LLVMGenerator.jump_label(body_label)

        # Loop body
        LLVMGenerator.define_label(body_label)
        self.visit(ctx.blockLabel)

        # Handle increment (only assignment allowed)
        if ctx.operation_assLabel:
            self.visit(ctx.operation_assLabel)

        # Jump back to condition
        LLVMGenerator.jump_label(cond_label)

        # Exit label
        LLVMGenerator.define_label(exit_label)
        return None
    
    def visitWhileStmt(self, ctx: MyLangParser.WhileStmtContext):
        # Generate unique labels for the while loop condition, body, and exit.
        loop_id = self.label_counter
        cond_label = f"while_cond_{loop_id}"
        body_label = f"while_body_{loop_id}"
        exit_label = f"while_exit_{loop_id}"
        self.label_counter += 3

        # Unconditionally jump to the condition block.
        LLVMGenerator.jump_label(cond_label)

        # Condition block: evaluate the loop condition.
        LLVMGenerator.define_label(cond_label)
        cond_reg, cond_type = self.visit(ctx.expr())
        if cond_type != "bool":
            self.error(ctx.start.line, "While loop condition must be boolean")
        # Branch to body if true, otherwise exit.
        LLVMGenerator.if_statement(cond_reg, body_label, exit_label)

        # While loop body.
        LLVMGenerator.define_label(body_label)
        self.visit(ctx.block())
        # After executing the body, jump back to re-check the condition.
        LLVMGenerator.jump_label(cond_label)

        # Exit point for the loop.
        LLVMGenerator.define_label(exit_label)
        return None
    
    def new_label(self):
        label = f"label_{self.label_counter}"
        self.label_counter += 1
        return label
    
    def visitParam(self, ctx):
        type = self.visit(ctx.advancedType())
        name = ctx.ID().getText()
        return (name,type)
    
    def visitParamList(self, ctx):
        values = []
        for child in ctx.getChildren():
            if isinstance(child, MyLangParser.ParamContext):
                values.append(self.visit(child))
        return values
    
    def build_array_sig(self, array_type):
        sizes, elem = array_type           
        llvm_elem   = self.getLLVMType(elem)

        typ = llvm_elem
        for s in reversed(sizes):
            typ = f"[{s} x {typ}]"
        return typ
    
    def visitFuncDecl(self, ctx: MyLangParser.FuncDeclContext):
        is_method  = self.class_name is not None
        fname      = f"{self.class_name}_{ctx.ID().getText()}" if is_method else ctx.ID().getText()

        self.current_function = fname      

        if ctx.paramList():
            params = self.visit(ctx.paramList())
        else:
            params = [] 

        param_sig_parts = []

        if is_method:
            llvm_class = f"%class.{self.class_name}*"
            param_sig_parts.append(f"{llvm_class} %this")
            
        for pn, pt in params:
            if isinstance(pt, tuple) and pt[1] == "struct":
                llvm_t = f"%struct.{pt[0]}*"
            elif isinstance(pt, tuple) and pt[1] == "class":
                llvm_t = f"%class.{pt[0]}*"
            elif isinstance(pt, tuple):           
                llvm_t = self.build_array_sig(pt) + "*"    
            else:
                llvm_t = self.getLLVMType(pt)
            param_sig_parts.append(f"{llvm_t} %{pn}")
        params_sig = ", ".join(param_sig_parts)
        
        is_generator = self._block_contains_yield(ctx.block())
        
        if is_generator:
            self.current_ret_type = (fname, 'generator')
            self._gen_current_type = None
            LLVMGenerator.enter_generator(f"{fname}.gen")
            self._current_gen_state = 0
        else:
            self.current_ret_type = 'void'
            LLVMGenerator.enter_function()
        
        self.variables.append({})
        
        if is_generator:
            for pn, pt in params:
                # global o nazwie  @<fname>_<param>
                glob = f"@{fname}_{pn}"

                # deklaracja globalna zgodnie z typem
                if   pt == "int":          LLVMGenerator.declare_int(glob)
                elif pt == "float":        LLVMGenerator.declare_float(glob)
                elif pt == "double":       LLVMGenerator.declare_double(glob)
                elif pt == "bool":         LLVMGenerator.declare_bool(glob)
                elif pt == "string":       LLVMGenerator.declare_string(glob)
                elif isinstance(pt, tuple): 
                    sizes, elem = pt
                    elem_llvm  = LLVMGenerator.llvm_type(elem)
                    arr_llvm   = LLVMGenerator.build_array(elem_llvm, sizes)
                    LLVMGenerator.declare_raw(f"@{fname}_{pn}", f"{arr_llvm} zeroinitializer")
                    self.variables[-1][pn] = VariableInfo(f"@{fname}_{pn}", pt)

                else:
                    self.error(ctx.start.line,
                            f"Nieobsługiwany typ parametru generatora: {pt}")

                # wrzuć do bieżącego scope-u, żeby  start/stop  były widoczne
                self.variables[-1][pn] = VariableInfo(glob, pt)
        
        if is_method:                      
            cls = self.class_name
            this_info = VariableInfo("%this", (cls, "class"))
            self.variables[-1]["this"] = this_info
            self.variables[-1]["self"] = this_info
        
        for pn, pt in params:
            if not is_generator:
                self.create_shadow_copy(pn, (f"%{pn}", pt), ctx) 

        if is_method:              
            self.variables[-1]["self"] = self.variables[-1]["this"]

        self.visit(ctx.block())

        if is_generator:
            llvm_t = self._gen_current_type
            if llvm_t is None:
                self.error(ctx.start.line,
                        "Generator function never yields a value")

            # mapowanie llvm-typu na typ języka
            elem_t = {'i32':'int', 'i8*':'string',
                    'float':'float', 'double':'double', "i1": "bool"}.get(llvm_t)
            if elem_t is None:
                self.error(ctx.start.line,
                        f"Nieznany typ zwracany przez generator: {llvm_t}")

            self.gen_elem_type[fname] = elem_t
            LLVMGenerator.finish_generator(fname,
                                        self._current_gen_state,
                                        llvm_t)
            LLVMGenerator.gen_wrapper(fname, params)
        else:
            LLVMGenerator.exit_function(fname, params_sig,
                                        self.getLLVMType(self.current_ret_type))
        
        self.scope_history.append(self.variables.pop())
        
        self.functions[fname] = dict(ret=self.current_ret_type, params=[t for _, t in params])
        if is_method:
            self.classes[self.class_name]['methods_map'][ctx.ID().getText()] = (
                self.current_ret_type, [t for _, t in params[1:]])
        self.variables[-1][fname] = VariableInfo(f"@{fname}", "func")
        return None

    def visitReturnStmt(self, ctx: MyLangParser.ReturnStmtContext):
        if ctx.expr():
            val_reg, val_type = self.visit(ctx.expr())
            self.current_ret_type = val_type
            llvm_t = self.getLLVMType(val_type)
            LLVMGenerator.buffor_stack[-1].append(
                f"ret {llvm_t} {val_reg}")
        else:
            self.current_ret_type = 'void'
            LLVMGenerator.buffor_stack[-1].append("ret void")

    def visitArgumentList(self, ctx):
        values = []
        for child in ctx.getChildren():
            if isinstance(child, MyLangParser.ExprContext):
                values.append(self.visit(child))
        return values

    def visitFuncCall(self, ctx: MyLangParser.FuncCallContext):
        res = self.visit(ctx.objectReference())
        hidden = []

        # --------------------------  obiekt + metoda  --------------------------
        if len(res) == 3:
            fname, ret_t, obj_ptr = res

            # poszukaj typu obiektu
            info = next(
                (inf for scope in reversed(self.variables + self.scope_history)
                for ln, inf in scope.items()
                if inf.name == obj_ptr or ln == obj_ptr.lstrip('@')),
                None
            )

            if info and isinstance(info.type_info, tuple) and info.type_info[1] == 'generator':
                # ----------  GENERATOR  ----------
                gen_name = info.type_info[0]              # np. 'oddNumbers'

                if obj_ptr.startswith('@'):
                    load_reg = LLVMGenerator.get_gen_ptr(obj_ptr, gen_name)
                    obj_ptr  = f"%{load_reg}"             # %oddNumbers.gen*

                hidden = [(obj_ptr, (gen_name, 'generator'))]

            else:
                # ----------  KLASA  ----------
                cls_name = self.get_class_name(obj_ptr)

                if obj_ptr.startswith('@'):
                    load_reg = LLVMGenerator.get_class_ptr(obj_ptr, cls_name)
                    obj_ptr  = f"%{load_reg}"             # %class.C*

                hidden = [(obj_ptr, (cls_name, 'class'))]

        else:                         # wywołanie wolnostojące
            fname, ret_t = res
            
        arg_values = self.visit(ctx.argumentList()) if ctx.argumentList() else []
        args = hidden + arg_values

        llvm_ret = self.getLLVMType(ret_t)

        arg_sig_parts = []
        for aval, at in args:
            if isinstance(at, tuple):
                tag = at[1]
                if tag == 'struct':
                    llvm_t = f"%struct.{at[0]}*"
                elif tag == 'class':
                    load_reg  = LLVMGenerator.get_class_ptr(aval, at[0])
                    aval = f"%{load_reg}"
                    llvm_t = f"%class.{at[0]}*"
                elif tag == 'generator':                       #  << NOWE >>
                    llvm_t = f"%{at[0]}.gen*"
                else:                    # prawdziwa tablica
                    llvm_t = self.build_array_sig(at) + "*"
            else:                        # typ prosty
                llvm_t = self.getLLVMType(at)

            arg_sig_parts.append(f"{llvm_t} {aval}")
        arg_sig = ", ".join(arg_sig_parts)

        if ret_t == 'void':
            LLVMGenerator.call_void_function(llvm_ret, fname, arg_sig)
            return (0, "bool")
        else:
            call_reg = LLVMGenerator.call_return_function(llvm_ret, fname, arg_sig)
            return (f"%{call_reg}", ret_t)

    def visitStructMember(self, ctx):
        member_name = ctx.ID().getText()
        member_type = self.visit(ctx.advancedType())
        return (member_name, member_type)

    def visitStructMemberList(self, ctx):
        members = []
        for index in ctx.getChildren():
            members.append(self.visit(index))
        return members

    def visitStructDecl(self, ctx: MyLangParser.StructDeclContext):
        sname = ctx.ID().getText()
        if sname in self.structs:
            self.error(ctx.start.line, f"Struct '{sname}' already defined")
            
        members = self.visit(ctx.structMemberList())
        self.structs[sname] = members

        total_size = 0
        for _name, el_type in members:
            if isinstance(el_type, tuple):
                length = 1
                for d in el_type[0]:
                    length *= int(d)

                total_size += length * 8
            else:
                total_size += 8 
        self.struct_sizes[sname] = total_size

        llvm_fields = []
        for _, t in members:
            if isinstance(t, tuple):
                llvm_fields.append(self.build_array_sig(t))
            else:
                llvm_fields.append(self.getLLVMType(t))

        struct_name = f"%struct.{sname}"

        LLVMGenerator.define_struct(struct_name, llvm_fields)
        
        return None
    

    def visitClassDecl(self, ctx: MyLangParser.ClassDeclContext): 
        class_name = ctx.ID().getText()
        self.class_name = class_name

        if class_name in self.classes or class_name in self.structs:
            self.error(ctx.start.line, f"Class '{class_name}' already defined")
        
        self._register_class(class_name, [], {})

        llvm_tys = []
        for fld in ctx.fieldDecl():
            fty = self.visit(fld.advancedType())
            idx = len(llvm_tys)
            self.classes[class_name]['fields_map'][fld.ID().getText()] = (idx, fty)
            llvm_tys.append(self.getLLVMType(fty))
        LLVMGenerator.define_class(class_name, llvm_tys)
        self.classes[class_name]['size'] = 8 * len(llvm_tys)

        for fld in ctx.fieldDecl():
            if fld.expr():
                self.visit(fld)

            self.variables.append({})

        # add 'this' and 'self' (so get_data_from_Scope("this") or ("self") works)
        this_info = VariableInfo(name="this", type_info=(class_name, "class"))
        self.variables[-1]["this"] = this_info
        self.variables[-1]["self"] = this_info

        # now inject *every* field into that scope
        # fields_map: { fieldName: (index, fieldType), … }
        # for field_name, (idx, field_type) in self.classes[class_name]["fields_map"].items():
        #     # compute the GEP for field_ptr = getelementptr %class.C, %class.C* %this, 0, idx
        #     # and bitcast it to the element pointer if you like; we'll just call your helper:
        #     ptr_reg = LLVMGenerator.get_class_field_ptr("this", class_name, idx)

        #     # record a VariableInfo so that get_data_from_Scope("x") → uses %<ptr_reg>
        #     self.variables[-1][field_name] = VariableInfo(
        #         name=f"%{ptr_reg}",
        #         type_info=field_type
        #     )

        for ctor in ctx.constructorDecl():
            self.visitConstructorDecl(ctor)
        for m in ctx.funcDecl():
            self.visit(m)

        self.variables.pop()
        self.class_name = None
        
        return None
    
    def visitConstructorDecl(self, ctx):
        fname = f"{self.class_name}_ctor"
        params = self.visit(ctx.paramList() or ctx)
        params = [("this", (self.class_name, "class"))] + params

        param_sig_parts = []
        for pn, pt in params:
            llvm_t = ("%class." + pt[0] + "*"
                      if isinstance(pt, tuple) and pt[1] == "class"
                      else "%struct." + pt[0] + "*"
                      if isinstance(pt, tuple) and pt[1] == "struct"
                      else self.getLLVMType(pt)
                      if not isinstance(pt, tuple)
                      else self.build_array_sig(pt) + "*")

            param_sig_parts.append(f"{llvm_t} %{pn}")
        params_sig = ", ".join(param_sig_parts)

        self.variables.append({})
        LLVMGenerator.enter_function()
        for pn, pt in params:
            self.create_shadow_copy(pn, (f"%{pn}", pt), ctx)
        
        self.visit(ctx.block())
        LLVMGenerator.exit_function(fname, params_sig, "void")
        self.scope_history.append(self.variables.pop())
        return None
    
    def visitClassMemberList(self, ctx):
        varDeclarations = []
        funcDeclarations = []
        constructorDeclarations = []
        for index in ctx.getChildren():
            member = self.visit(index)
            if "var" in member:
                varDeclarations.append(member["var"])
            elif "func" in member:
                funcDeclarations.append(member["func"])
            elif "constructor" in member:
                constructorDeclarations.append(member["constructor"])
        return varDeclarations, funcDeclarations, constructorDeclarations

    def visitClassMember(self, ctx):
        if ctx.varDecl():
            return {"var" : self.visit(ctx.varDecl())}
        elif ctx.funcDecl():
            return {"func" : self.visit(ctx.funcDecl())}
        elif ctx.constructorDecl():
            return {"constructor" : self.visit(ctx.constructorDecl())}

    def _block_contains_yield(self, node):
        # 1) bezpośrednio trafiliśmy na węzeł 'yield'
        if isinstance(node, MyLangParser.YieldStmtContext):   #  ← kluczowa zmiana
            return True

        # 2) liść drzewa (token) – nie ma dzieci
        if not hasattr(node, "getChildCount"):
            return False

        # 3) rekurencyjnie sprawdź wszystkie dzieci
        for i in range(node.getChildCount()):
            if self._block_contains_yield(node.getChild(i)):
                return True
        return False

    def visitYieldStmt(self, ctx: MyLangParser.YieldStmtContext):
        val_reg, val_type = self.visit(ctx.expr())
        llvm_t = self.getLLVMType(val_type)

        # ► jeżeli jeszcze nie zdefiniowaliśmy struct-a z tym typem
        if self._gen_current_type is None:
            self._gen_current_type = llvm_t
            LLVMGenerator.define_generator_struct(self.current_function, llvm_t)

        state_id = self._current_gen_state
        self._current_gen_state += 1

        LLVMGenerator.emit_yield(llvm_t, val_reg, state_id)
        return (0, "void")
