from antlr4 import *
import sys

class LLVMGenerator:
    header_text = []
    reg = 1
    str_counter = 1
    buffor_stack = [[]]

    @staticmethod
    def reset():
        LLVMGenerator.header_text = []
        LLVMGenerator.reg = 1
        LLVMGenerator.str_counter = 1
        LLVMGenerator.buffor_stack = [[]]

    # region Primitive Types

    # region Declarations

    @staticmethod
    def declare_int(var_name):
        LLVMGenerator.header_text.append(f"{var_name} = global i32 0")

    @staticmethod
    def declare_float(var_name):
        LLVMGenerator.header_text.append(f"{var_name} = global float 0.0")

    @staticmethod
    def declare_double(var_name):
        LLVMGenerator.header_text.append(f"{var_name} = global double 0.0")

    @staticmethod
    def declare_string(var_name, size=256):
        LLVMGenerator.header_text.append(f"{var_name} = global i8* null")

    @staticmethod
    def declare_bool(var_name):
        LLVMGenerator.header_text.append(f"{var_name} = global i1 false")

    # endregion
    
    # region Assignments
    @staticmethod
    def assign_int(var_name, value):
        LLVMGenerator.buffor_stack[-1].append(f"store i32 {value}, i32* {var_name}")

    @staticmethod
    def assign_float(var_name, value):
        LLVMGenerator.buffor_stack[-1].append(f"store float {value}, float* {var_name}")

    @staticmethod
    def assign_double(var_name, value):
        LLVMGenerator.buffor_stack[-1].append(f"store double {value}, double* {var_name}")

    @staticmethod
    def assign_string(var_name, value):
        LLVMGenerator.buffor_stack[-1].append(f"store i8* {value}, i8** {var_name}")

    @staticmethod
    def assign_bool(var_name, value):
        LLVMGenerator.buffor_stack[-1].append(f"store i1 {value}, i1* {var_name}")

    # endregion
    
    # region Loads
    @staticmethod
    def load_int(var_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = load i32, i32* {var_name}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def load_bool(var_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = load i1, i1* {var_name}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def load_float(var_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = load float, float* {var_name}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def load_double(var_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = load double, double* {var_name}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def load_string(var_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = load i8*, i8** {var_name}")
        LLVMGenerator.reg += 1
        return reg

    # endregion

    # region Projections
    @staticmethod
    def int_to_float(reg_val):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = sitofp i32 {reg_val} to float")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def float_to_double(reg_val):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fpext float {reg_val} to double")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def float_to_int(reg_val):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fptosi float {reg_val} to i32")
        LLVMGenerator.reg += 1
        return reg
    
    @staticmethod
    def int_to_double(reg_val):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = sitofp i32 {reg_val} to double")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def double_to_int(reg_val):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fptosi double {reg_val} to i32")
        LLVMGenerator.reg += 1
        return reg
    # endregion

    # region Reads
    @staticmethod
    def read_int(var_name):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @scanf(i8* getelementptr inbounds ([3 x i8], [3 x i8]* @stri, i32 0, i32 0), i32* {var_name})"
        )
        LLVMGenerator.reg += 1

    @staticmethod
    def read_float(var_name):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @scanf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @strf, i32 0, i32 0), float* {var_name})"
        )
        LLVMGenerator.reg += 1

    @staticmethod
    def read_double(var_name):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @scanf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @strlf, i32 0, i32 0), double* {var_name})"
        )
        LLVMGenerator.reg += 1


    @staticmethod
    def read_string(var_name, size=256):
        # Alokacja bloku pamięci dla danych typu string (256 bajtów)
        LLVMGenerator.header_text.append(f"@str{LLVMGenerator.str_counter} = global [{size} x i8] zeroinitializer")
        # Pobranie wskaźnika do początku bloku
        LLVMGenerator.buffor_stack[-1].append(f"%ptr_str{LLVMGenerator.str_counter} = getelementptr inbounds [{size} x i8], [{size} x i8]* @str{LLVMGenerator.str_counter}, i32 0, i32 0")
        # Przypisanie wskaźnika do zmiennej
        LLVMGenerator.buffor_stack[-1].append(f"store i8* %ptr_str{LLVMGenerator.str_counter}, i8** {var_name}")
        # Wywołanie scanf – używamy formatu "%255s" (256 bajtów łącznie)
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @scanf(i8* getelementptr inbounds ([6 x i8], [6 x i8]* @strs, i32 0, i32 0), i8* %ptr_str{LLVMGenerator.str_counter})"
        )
        LLVMGenerator.reg += 1
        LLVMGenerator.str_counter += 1
    # endregion
    
    # region Prints
    @staticmethod
    def print_int(reg_val):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @strp_int, i32 0, i32 0), i32 {reg_val})"
        )
        LLVMGenerator.reg += 1

    @staticmethod
    def print_float(reg_val):
        reg_ext = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg_ext} = fpext float {reg_val} to double"
        )
        LLVMGenerator.reg += 1
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([6 x i8], [6 x i8]* @strp_double, i32 0, i32 0), i32 9, double %{reg_ext})"
        )
        LLVMGenerator.reg += 1


    @staticmethod
    def print_double(reg_val):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([6 x i8], [6 x i8]* @strp_double, i32 0, i32 0), i32 17, double {reg_val})"
        )
        LLVMGenerator.reg += 1

    @staticmethod
    def print_string(reg_val):
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @strp_str, i32 0, i32 0), i8* {reg_val})"
        )
        LLVMGenerator.reg += 1

    @staticmethod
    def print_bool(reg_val):
        # Since printf may not support i1 directly, extend it to i32:
        reg_int = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg_int} = zext i1 {reg_val} to i32")
        LLVMGenerator.reg += 1
        LLVMGenerator.buffor_stack[-1].append(
            f"%{LLVMGenerator.reg} = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @strp_int, i32 0, i32 0), i32 %{reg_int})"
        )
        LLVMGenerator.reg += 1


    # endregion

    # endregion

    # region Arrays

    @staticmethod
    def build_array(element_type, sizes):
        if not isinstance(sizes, tuple):
            sizes = (sizes, )
        if len(sizes) == 0:
            return element_type
        else:
            return f"[{sizes[0]} x {LLVMGenerator.build_array(element_type, sizes[1:])}]"   

    @staticmethod
    def declare_array(var_name, element_type, sizes):
        array = LLVMGenerator.build_array(element_type, sizes)
        LLVMGenerator.header_text.append(f"{var_name} = global {array} zeroinitializer")

    @staticmethod
    def get_array_element_ptr(var_name, indices, element_type, sizes):
        array = LLVMGenerator.build_array(element_type, sizes)
        reg = LLVMGenerator.reg
        if not isinstance(indices, list):
            indices = [indices]
        all_indices = [0] + indices
        indices_str = ", ".join([f"i32 {idx}" for idx in all_indices])
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = getelementptr inbounds {array}, {array}* {var_name}, {indices_str}"
        )
        LLVMGenerator.reg += 1
        return reg
    
    @staticmethod
    def store_array_element(var_name, indices, value, element_type, sizes):
        ptr_reg = LLVMGenerator.get_array_element_ptr(var_name, indices, element_type, sizes)
        LLVMGenerator.buffor_stack[-1].append(
            f"store {element_type} {value}, {element_type}* %{ptr_reg}"
        )
        return ptr_reg

    @staticmethod
    def load_array_element(element_type, ptr_reg):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = load {element_type}, {element_type}* %{ptr_reg}"
        )
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def memcpy(dest, src, total_size, align, src_type):
        reg_src_cast = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg_src_cast} = bitcast {src_type}* {src} to i8*"
        )
        LLVMGenerator.reg += 1

        LLVMGenerator.buffor_stack[-1].append(
            f"call void @llvm.memcpy.p0i8.p0i8.i64(i8* align {align} {dest}, i8* align {align} %{reg_src_cast}, i64 {total_size}, i1 false)"
        )

    #endregion

    # region Strings
    @staticmethod
    def constant_string(value):
        # Długość łańcucha + 1 (na znak null)
        l = len(value) + 1
        str_id = LLVMGenerator.str_counter

        # Globalna stała zawierająca łańcuch znaków
        LLVMGenerator.header_text.append(
            f'@const_str{str_id} = constant [{l} x i8] c"{value}\\00"'
        )

        # Globalna zmienna (kopii) — zeroinicjalizowana
        LLVMGenerator.header_text.append(
            f"@str{str_id} = global [{l} x i8] zeroinitializer"
        )

        # W funkcji main kopiujemy zawartość stałej do zmiennej globalnej
        LLVMGenerator.buffor_stack[-1].append(
            f"%tmp{str_id} = bitcast [{l} x i8]* @str{str_id} to i8*"
        )
        LLVMGenerator.buffor_stack[-1].append(
            f"call void @llvm.memcpy.p0i8.p0i8.i64("
            f"i8* align 1 %tmp{str_id}, "
            f"i8* align 1 getelementptr inbounds ([{l} x i8], [{l} x i8]* @const_str{str_id}, i32 0, i32 0), "
            f"i64 {l}, i1 false)"
        )

        LLVMGenerator.str_counter += 1
        return f"@str{str_id}"
    
    #endregion

    # region math operations
    @staticmethod
    def sub_int(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = sub i32 {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def sub_float(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fsub float {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def sub_double(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fsub double {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

  
    @staticmethod
    def mul_int(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = mul i32 {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def mul_float(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fmul float {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def mul_double(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fmul double {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def div_int(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = sdiv i32 {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def div_float(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fdiv float {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def div_double(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fdiv double {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg


    @staticmethod
    def add_int(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = add i32 {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def add_float(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fadd float {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def add_double(reg1, reg2):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fadd double {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg

    # endregion

    # region Logical operations

    @staticmethod
    def or_expr(reg1, rhs_builder):
        reg = LLVMGenerator.reg
        end_label = f"or_end_{reg}"
        true_label = f"or_true_{reg}"
        rhs_label = f"or_rhs_{reg}"

        LLVMGenerator.buffor_stack[-1].append(f"br i1 {reg1}, label %{true_label}, label %{rhs_label}")
        
        LLVMGenerator.buffor_stack[-1].append(f"{true_label}:")
        LLVMGenerator.buffor_stack[-1].append(f"br label %{end_label}")
        LLVMGenerator.buffor_stack[-1].append(f"{rhs_label}:")
        rhs_reg = rhs_builder()
        LLVMGenerator.buffor_stack[-1].append(f"br label %{end_label}")
        LLVMGenerator.buffor_stack[-1].append(f"{end_label}:")

        phi_reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{phi_reg} = phi i1 [ 1, %{true_label} ], [ {rhs_reg}, %{rhs_label} ]")  

        LLVMGenerator.reg += 1

        return phi_reg
    
    @staticmethod
    def and_expr(reg1, rhs_builder):
        reg = LLVMGenerator.reg
        end_label = f"and_end_{reg}"
        rhs_label = f"and_rhs_{reg}"
        false_label = f"and_false_{reg}"

        LLVMGenerator.buffor_stack[-1].append(f"br i1 {reg1}, label %{rhs_label}, label %{false_label}")

        LLVMGenerator.buffor_stack[-1].append(f"{false_label}:")
        LLVMGenerator.buffor_stack[-1].append(f"br label %{end_label}")
        LLVMGenerator.buffor_stack[-1].append(f"{rhs_label}:")
        rhs_reg = rhs_builder()
        LLVMGenerator.buffor_stack[-1].append(f"br label %{end_label}")
        LLVMGenerator.buffor_stack[-1].append(f"{end_label}:")

        phi_reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{phi_reg} = phi i1 [ 0, %{false_label} ], [ {rhs_reg}, %{rhs_label} ]")  

        LLVMGenerator.reg += 1

        return phi_reg
    
    @staticmethod
    def xor_expr(reg1, reg2):
        reg = LLVMGenerator.reg

        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = xor i1 {reg1}, {reg2}")

        LLVMGenerator.reg += 1

        return reg

    @staticmethod
    def neg_expr(reg1):
        reg = LLVMGenerator.reg

        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = xor i1 {reg1}, 1")

        LLVMGenerator.reg += 1

        return reg

    @staticmethod
    def eq_expr_int(condition, reg1, reg2, type_str):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = icmp {condition} {type_str} {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg
    
    @staticmethod
    def eq_expr_f_db(condition, reg1, reg2, type_str):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = fcmp {condition} {type_str} {reg1}, {reg2}")
        LLVMGenerator.reg += 1
        return reg
    
    # endregion
    
    # region Ifs and loops
    
    @staticmethod
    def if_statement(cond_reg, true_label, false_label):
        LLVMGenerator.buffor_stack[-1].append(f"br i1 {cond_reg}, label %{true_label}, label %{false_label}")
        
    @staticmethod
    def define_label(label):
        LLVMGenerator.buffor_stack[-1].append(f"{label}:")

    @staticmethod
    def jump_label(label):
        LLVMGenerator.buffor_stack[-1].append(f"br label %{label}")

    @staticmethod
    def strcmp_call(left_reg, right_reg):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = call i32 @strcmp(i8* {left_reg}, i8* {right_reg})"
        )
        LLVMGenerator.reg += 1
        
        return reg
            
    # endregion

    # region funcion
    @staticmethod
    def enter_function():
        LLVMGenerator.buffor_stack.append([])

    @staticmethod
    def exit_function(name, params_sig, ret_type):
        body = LLVMGenerator.buffor_stack.pop()
        
        terminators = ("ret", "br", "switch", "resume", "unreachable")
        if not body or not body[-1].lstrip().startswith(terminators):
            if ret_type == "void":
                body.append("ret void")
            else:
                body.append(f"ret {ret_type} undef")
        
        LLVMGenerator.header_text.append(f"define {ret_type} @{name}({params_sig}) {{")
        for instr in body:
            LLVMGenerator.header_text.append("  " + instr)
        LLVMGenerator.header_text.append("}")
        
    
    @staticmethod
    def call_void_function(llvm_ret, fname, arg_sig):
        LLVMGenerator.buffor_stack[-1].append(f"call {llvm_ret} {fname}({arg_sig})")
        
    @staticmethod
    def call_return_function(llvm_ret, fname, arg_sig):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg} = call {llvm_ret} {fname}({arg_sig})")
        LLVMGenerator.reg += 1
        return reg
    
    # endregion
            
    # region Structures
    
    @staticmethod
    def define_struct(struct_name, struct_elems):
        LLVMGenerator.header_text.append(f"{struct_name} = type {{ {', '.join(struct_elems)} }}")

    @staticmethod
    def declare_struct(var_name, type_info):
        LLVMGenerator.header_text.append(f"{var_name} = global %struct.{type_info}* null")
    
    @staticmethod
    def initialize_struct(var_name, type_info, total_size):
        reg1 = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{reg1} = call i8* @malloc(i64 {total_size})")
        LLVMGenerator.reg +=1
        reg2 = LLVMGenerator.reg

        LLVMGenerator.buffor_stack[-1].append(f"%{reg2} = bitcast i8* %{reg1} to %struct.{type_info}*")
        LLVMGenerator.buffor_stack[-1].append(f"store %struct.{type_info}* %{reg2}, %struct.{type_info}** {var_name}")
        LLVMGenerator.reg +=1
        
        return reg2

    @staticmethod
    def get_struct_ptr(var_name, struct_name):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = load %struct.{struct_name}*, %struct.{struct_name}** {var_name}"
        )
        LLVMGenerator.reg +=1
        return reg
    
    @staticmethod                 
    def get_struct_field_ptr(base_ptr, struct_name, index):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = getelementptr inbounds %struct.{struct_name}, %struct.{struct_name}* %{base_ptr}, i32 0, i32 {index}")
        LLVMGenerator.reg += 1
        return f"%{reg}"
    
    @staticmethod
    def bitcast(src, src_type):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = bitcast {src_type}* {src} to i8*"
        )
        LLVMGenerator.reg += 1
        return reg
        
    # endregion

    # region Classes
    @staticmethod
    def define_class(class_name, llvm_fields):
        LLVMGenerator.header_text.append(f"%class.{class_name} = type {{ {', '.join(llvm_fields)} }}")

    @staticmethod
    def allocate_class(class_name, total_size):
        r_malloc = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{r_malloc} = call i8* @malloc(i64 {total_size})")
        LLVMGenerator.reg += 1

        r_obj = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(f"%{r_obj} = bitcast i8* %{r_malloc} to %class.{class_name}*")
        LLVMGenerator.reg += 1
        return r_obj
    
    @staticmethod
    def declare_class(var_name, type_info):
        LLVMGenerator.header_text.append(f"{var_name} = global %class.{type_info}* null")
    
    @staticmethod
    def get_class_field_ptr(base_ptr, class_name, field_index):
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = getelementptr inbounds %class.{class_name}, "
            f"%class.{class_name}* {base_ptr}, i32 0, i32 {field_index}"
        )
        LLVMGenerator.reg += 1
        return reg
    
    @staticmethod
    def get_class_ptr(var_name, class_name):
        if var_name.startswith('%'):
            return var_name.lstrip('%')     
        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = load %class.{class_name}*, %class.{class_name}** {var_name}"
        )
        LLVMGenerator.reg += 1
        return reg
        
    @staticmethod
    def store_class(var_name, type_info, ptr):
        LLVMGenerator.buffor_stack[-1].append(f"store %class.{type_info}* %{ptr}, %class.{type_info}** {var_name}")
    
    # endregion    

    # region Generator Function
    
    @staticmethod
    def define_generator_struct(gen_name, ret_llvm_type):
        """
        %gen_name.gen = type { i32 state, retType current }
        """
        LLVMGenerator.header_text.append(
            f"%{gen_name}.gen = type {{ i32, {ret_llvm_type} }}"
        )

    @staticmethod
    def emit_yield(ret_llvm_type, val_reg, state_id):
        """
        • zapisuje wartość do pola current
        • ustawia następny state
        • ret 1   + etykieta gen_resume_<id>
        """
        # --- current -------------------------------------------------------
        cur_ptr = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{cur_ptr} = getelementptr %{LLVMGenerator._active_gen}, "
            f"%{LLVMGenerator._active_gen}* %self, i32 0, i32 1")
        LLVMGenerator.reg += 1
        LLVMGenerator.buffor_stack[-1].append(
            f"store {ret_llvm_type} {val_reg}, {ret_llvm_type}* %{cur_ptr}")

        # --- state ---------------------------------------------------------
        st_ptr = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{st_ptr} = getelementptr %{LLVMGenerator._active_gen}, "
            f"%{LLVMGenerator._active_gen}* %self, i32 0, i32 0")
        LLVMGenerator.reg += 1
        LLVMGenerator.buffor_stack[-1].append(
            f"store i32 {state_id+1}, i32* %{st_ptr}")

        # --- zakończenie ---------------------------------------------------
        LLVMGenerator.buffor_stack[-1].append("ret i1 1")
        LLVMGenerator.define_label(f"gen_resume_{state_id}")

        # do dispatcher-switch
        LLVMGenerator._state_cases.append(state_id + 1)

    @staticmethod
    def enter_generator(gen_struct):
        LLVMGenerator._active_gen = gen_struct
        LLVMGenerator.enter_function()

        # ── dispatcher ─────────────────────────────────────────────
        LLVMGenerator.buffor_stack[-1].append(
            f"%state_ptr = getelementptr %{gen_struct}, "
            f"%{gen_struct}* %self, i32 0, i32 0")
        LLVMGenerator.buffor_stack[-1].append(
            "%state = load i32, i32* %state_ptr")
        # na razie pusta lista przypadków, uzupełnimy ją w finish_generator
        LLVMGenerator.buffor_stack[-1].append(
            "switch i32 %state, label %gen_entry [  ]")
        
        LLVMGenerator._switch_idx  = len(LLVMGenerator.buffor_stack[-1]) - 1  # zapamiętaj pozycję 'switch'
        LLVMGenerator._state_cases = []        

        LLVMGenerator.define_label("gen_entry")          # tu zacznie się „stan-0”


    @staticmethod
    def finish_generator(fname, last_state_id, ret_llvm_type):
        """
        Kończy funkcję .next oraz dokleja .create wrapper
        """
        cases = " ".join(         
            f"i32 {sid}, label %gen_resume_{sid-1}"
            for sid in LLVMGenerator._state_cases
        )
        switch_idx = LLVMGenerator._switch_idx
        old = LLVMGenerator.buffor_stack[-1][switch_idx]
        LLVMGenerator.buffor_stack[-1][switch_idx] = old[:-2] + cases + " ]"
        # blok końcowy – gdy state > last_state_id
        LLVMGenerator.buffor_stack[-1].append("br label %gen_stop")
        LLVMGenerator.define_label("gen_stop")
        LLVMGenerator.buffor_stack[-1].append("ret i1 0")

        LLVMGenerator.exit_function(f"{fname}_next",
                                    f"%{fname}.gen* %self",
                                    "i1")

        # konstruktor
        LLVMGenerator.enter_function()
        LLVMGenerator.buffor_stack[-1].append(
            f"%mem = call i8* @malloc(i64 16)")   # 2× i64 = 16 B
        LLVMGenerator.buffor_stack[-1].append(
            f"%self = bitcast i8* %mem to %{fname}.gen*")
        LLVMGenerator.buffor_stack[-1].append(
            f"%st = getelementptr %{fname}.gen, %{fname}.gen* %self, i32 0, i32 0")
        LLVMGenerator.buffor_stack[-1].append(
            "store i32 0, i32* %st")
        LLVMGenerator.buffor_stack[-1].append(f"ret %{fname}.gen* %self")
        LLVMGenerator.exit_function(f"{fname}_create", "", f"%{fname}.gen*")


    @staticmethod
    def get_gen_current(ptr, gen_name, llvm_t):
        # ptr → '@g' lub '%tmp'
        if ptr.startswith('@'):
            r0 = LLVMGenerator.reg
            LLVMGenerator.buffor_stack[-1].append(
                f"%{r0} = load %{gen_name}.gen*, %{gen_name}.gen** {ptr}")
            LLVMGenerator.reg += 1
            ptr_val = f"%{r0}"
        else:
            ptr_val = ptr

        r1 = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{r1} = getelementptr %{gen_name}.gen, %{gen_name}.gen* {ptr_val}, i32 0, i32 1")
        LLVMGenerator.reg += 1
        r2 = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{r2} = load {llvm_t}, {llvm_t}* %{r1}")
        LLVMGenerator.reg += 1
        return r2

    @staticmethod
    def llvm_type(pt):
        """
        Zamienia opis typu z LLVMActions (pt) na llvm-typ wraz z gwiazdką,
        którego możesz używać w sygnaturach funkcji.
        """
        # typ prosty
        if not isinstance(pt, tuple):
            return {"int":"i32",
                    "float":"float",
                    "double":"double",
                    "bool":"i1",
                    "string":"i8*"}.get(pt, pt)

        tag = pt[1]
        if tag == "struct":
            return f"%struct.{pt[0]}*"
        if tag == "class":
            return f"%class.{pt[0]}*"
        if tag == "generator":
            return f"%{pt[0]}.gen*"

        # prawdziwa tablica  (sizes, elem_type)
        sizes, elem = pt
        elem_llvm = LLVMGenerator.llvm_type(elem)        # rekursja działa, bo elem to prymityw
        return LLVMGenerator.build_array(elem_llvm, sizes) + "*"

    @staticmethod
    def get_gen_ptr(var_name, gen_name):
        """
        Ładuje wskaźnik do struktury generatora z globalnej zmiennej.
        var_name  – @g albo %tmp
        gen_name  – 'nazwaFunkcji'
        Zwraca numer nowego rega.
        """
        if var_name.startswith('%'):          # już mamy %oddNumbers.gen*
            return var_name.lstrip('%')

        reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{reg} = load %{gen_name}.gen*, %{gen_name}.gen** {var_name}"
        )
        LLVMGenerator.reg += 1
        return reg

    @staticmethod
    def declare_raw(global_name: str, llvm_definition: str):
        """
        Rejestruje dowolną (już zbudowaną) deklarację globalną.
        Używane m.in. przez LLVMActions przy generowaniu tablic-parametrów
        dla generatorów.
        """
        LLVMGenerator.header_text.append(f"{global_name} = global {llvm_definition}")

    @staticmethod
    def sizeof_primitive(llvm_elem_ty: str) -> int:
        return {
            "i1": 1,
            "i32": 4,
            "float": 4,
            "double": 8,
            "i8*": 8         # wskaźnik na string
        }.get(llvm_elem_ty, 8)  # domyślnie pointer-size

    @staticmethod
    def gen_wrapper(fname, params):
        # ─── 1. sygnatura funkcji ─────────────────────────────────────────────
        sig_parts = [
            f"{LLVMGenerator.llvm_type(pt)} %{pn}"
            for pn, pt in params
        ]
        params_sig = ", ".join(sig_parts)

        # ─── 2. ciało wrappera ────────────────────────────────────────────────
        LLVMGenerator.enter_function()

        # kopia argumentów do globali @<fname>_<param>
        for pn, pt in params:
            llvm_t = LLVMGenerator.llvm_type(pt)

            # ── parametr to statyczna tablica ───────────────────
            if llvm_t.endswith('*') and llvm_t[0] == '[':
                dim   = int(llvm_t[1:].split('x')[0].strip())
                elem  = llvm_t.split('x')[1].split(']')[0].strip()
                bytes = dim * LLVMGenerator.sizeof_primitive(elem)

                # %tmpDst = bitcast [N x T]* @foo_arr  to i8*
                dst_reg = LLVMGenerator.reg
                LLVMGenerator.buffor_stack[-1].append(
                    f"%{dst_reg} = bitcast {llvm_t} @{fname}_{pn} to i8*")
                LLVMGenerator.reg += 1

                # %tmpSrc = bitcast [N x T]* %{pn}     to i8*
                src_reg = LLVMGenerator.reg
                LLVMGenerator.buffor_stack[-1].append(
                    f"%{src_reg} = bitcast {llvm_t} %{pn} to i8*")
                LLVMGenerator.reg += 1

                LLVMGenerator.buffor_stack[-1].append(
                    f"call void @llvm.memcpy.p0i8.p0i8.i64("
                    f"i8* %{dst_reg}, i8* %{src_reg}, i64 {bytes}, i1 false)")
            # ── każdy inny typ ──────────────────────────────────
            else:
                LLVMGenerator.buffor_stack[-1].append(
                    f"store {llvm_t} %{pn}, {llvm_t}* @{fname}_{pn}")

        # wywołanie  *_create()  i zwrot wskaźnika
        g_reg = LLVMGenerator.reg
        LLVMGenerator.buffor_stack[-1].append(
            f"%{g_reg} = call %{fname}.gen* @{fname}_create()"
        )
        LLVMGenerator.reg += 1
        LLVMGenerator.buffor_stack[-1].append(
            f"ret %{fname}.gen* %{g_reg}"
        )

        # ─── 3. zamknięcie funkcji ────────────────────────────────────────────
        LLVMGenerator.exit_function(fname, params_sig, f"%{fname}.gen*")



    # endregion

    @staticmethod
    def generate():
        declarations = [
            'target triple = "x86_64-pc-windows-msvc"',
            'declare i32 @printf(i8*, ...)',
            'declare i32 @scanf(i8*, ...)',
            'declare i32 @strcmp(i8*, i8*)',
            '@strp_int = constant [4 x i8] c"%d\\0A\\00"',
            '@strp_double = constant [6 x i8] c"%.*g\\0A\\00"',
            '@strp_str = constant [4 x i8] c"%s\\0A\\00"',
            '@stri = constant [3 x i8] c"%d\00"',
            '@strs = constant [6 x i8] c"%255s\\00"',
            '@strf = constant [3 x i8] c"%f\\00"',
            '@strlf = constant [4 x i8] c"%lf\\00"',
            'declare i8* @malloc(i64)'
        ]
        
        if len(LLVMGenerator.buffor_stack) != 1:
            print(f"Error in function clousures")
            sys.exit(1)
        
        return "\n".join(declarations) + "\n" + "\n".join(LLVMGenerator.header_text) + "\n" + \
               "define i32 @main() {\n" + "\n".join(LLVMGenerator.buffor_stack[-1]) + "\nret i32 0\n}\n"
