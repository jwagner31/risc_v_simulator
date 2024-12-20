import re

class PipelineSimulator:
    def __init__(self, instructions, trace_start=None, trace_end=None, output_file_name_2=None):
        # Input list of decoded instructions from disassembler
        self.instructions = self.convert_instructions(instructions)
        self.output_file_name_2 = output_file_name_2
        # initialize pipeline as a dictionary with stages as keys
        nop_instruction = {"operation": "NOP", "operands": [], "address": None, "string": "NOP"}
        self.pipeline = {
            "IF": nop_instruction,
            "IS": nop_instruction,
            "ID": nop_instruction,
            "RF": nop_instruction,
            "EX": nop_instruction,
            "DF": nop_instruction,
            "DS": nop_instruction,
            "WB": nop_instruction
        }
        self.clock_cycle = 0              
        self.trace_start = trace_start    
        self.trace_end = trace_end        

        self.registers = {f"R{i}": 0 for i in range(32)}  # 32 registers as a dictionary
        self.memory = {i: 0 for i in range(600, 640, 4)}    # Dictionary to represent memory space from address 600 to 636

        self.total_stalls = 0
        self.total_forwardings = 0
        self.load_stalls = 0
        self.branch_stalls = 0
        self.other_stalls = 0
        
        self.forwarding_counts = {
            "EX/DF -> RF/EX": 0,
            "DF/DS -> EX/DF": 0,
            "DF/DS -> RF/EX": 0,
            "DS/WB -> EX/DF": 0,
            "DS/WB -> RF/EX": 0
        }

        self.forwarding_print = {
            "EX/DF -> RF/EX": "",
            "DF/DS -> EX/DF": "",
            "DF/DS -> RF/EX": "",
            "DS/WB -> EX/DF": "",
            "DS/WB -> RF/EX": ""
        }


        # instruction_needing_forwarding -> list( possible forwarding_sources)
        self.forwarding_detected = {}
        
        self.pipeline_registers = {
            "IF/IS": {"NPC": 0},
            "IS/ID": {"IR": nop_instruction},
            "RF/EX": {"A": 0, "B": 0},
            "EX/DF": {"ALUout": 0, "B": 0},
            "DF/DS": {"ALUout_LMD": 0, "ALUout_LMD_B": 0},
            "DS/WB": {"ALUout_LMD": 0}
        }
        
        self.is_pipeline_complete = False

        self.pc = 496
        self.stall_counter = 0
        self.stall_flag = False

    def simulate(self):
        # Main loop of stuff
        for i in range(self.trace_end):
            if self.is_pipeline_complete:
                break
            self.advance_pipeline()
            self.clock_cycle += 1
        self.print_final_summary()

    def convert_instructions(self, instruction_lines):
        formatted_instructions = []

        for line in instruction_lines:
            # Replace all tab characters with spaces
            formatted_line = line.replace('\t', ' ')
            formatted_instructions.append(formatted_line)
        
        return formatted_instructions
    
    def parse_instruction(self, instruction):
        # Parse the given instruction string and return a dictionary of components
        parts = instruction.split()
        if len(parts) < 4:
            return {"operation": "NOP", "operands": [None, None, None], "address": None, "string": "NOP"}
        asm_str = ""
        for i in range(7, len(parts)):
            asm_str += parts[i] + " "

        address = int(parts[6])
        # Split asm_str into operation and operands
        operation = parts[7]  # Operation nam
        #Special Case: J 
        if operation == "J":
            parsed_instr = {
                "string": parts[7] + " " + parts[8],
                "operation": operation,
                "operands": [parts[8][1:len(parts[8])]],
                "address": address
            }
            return parsed_instr
        if asm_str == "ADDI x0, x0, 0 ":
            parsed_instr = {
                "string": "NOP",
                "operation": "NOP",
                "operands": [None, None, None],
                "address": address
            }
            return parsed_instr
        if operation == "RET":
            parsed_instr = {
                "string": "BREAK",
                "operation": "NOP",
                "operands": [None, None, None],
                "address": address
            }
            return parsed_instr

        operands = [op.replace('x', 'R').replace(',', '') for op in parts[8:]]  # swap 'x' with 'R' and remove commas

        parsed_instr = {
            "string": asm_str,
            "operation": operation,
            "operands": operands,
            "address": address
        }
        return parsed_instr

    def advance_pipeline(self):

        if self.stall_counter > 0:
            self.stall_counter -= 1
            self.total_stalls += 1
            self.load_stalls += 1
            self.stall_flag = True
        elif self.stall_counter == 0:
            self.stall_flag = False

        self.pipeline["WB"] = self.pipeline["DS"]
        self.pipeline["DS"] = self.pipeline["DF"]
        self.pipeline["DF"] = self.pipeline["EX"]
        self.pipeline["EX"] = self.pipeline["RF"]
        if not self.stall_flag:
            self.pipeline["RF"] = self.pipeline["ID"]
            self.pipeline["ID"] = self.pipeline["IS"]
            self.pipeline["IS"] = self.pipeline["IF"]
            self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}  # Reset IF stage to NOP
        else:
            self.pipeline["RF"] = {"operation": "NOP", "operands": [None, None, None], "address": None, "string": "** STALL **"}
            


        # Write Back to registers
        if self.pipeline["WB"]["operation"] != "NOP":
            instruction = self.pipeline["WB"]
            if instruction["operation"] in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                dest_reg = instruction["operands"][0]
                result = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                self.registers[dest_reg] = result
            elif instruction["operation"] in ["LW"]:
                dest_reg = instruction["operands"][0]
                result = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                self.registers[dest_reg] = result
                if self.pipeline["DS"]["string"] == "** STALL **" and self.pipeline["EX"]["operands"][2] == dest_reg:
                    self.pipeline_registers["RF/EX"]["B"] = result
                    self.forwarding_counts["DS/WB -> RF/EX"] += 1
                    self.forwarding_print["DS/WB -> RF/EX"] = f"({instruction['string']}) to ({self.pipeline['EX']['string']})"
            elif instruction["operation"] == "J":
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = 0

        # DS Stage
        if self.pipeline["DS"]["operation"] != "NOP":
            instruction = self.pipeline["DS"]
            operation = instruction["operation"]

            if instruction["string"] in self.forwarding_detected:
                del self.forwarding_detected[instruction["string"]]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
            elif operation in ["SW"]:
                # need to store the value currently in the 
                address = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                value = self.pipeline_registers["DF/DS"]["ALUout_LMD_B"]
                self.memory[address] = value
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = address

            elif operation in ["LW"]:
                address = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.memory[address]
            elif operation in ["BEQ", "BNE", "BLT", "BGE", "JAL", "JALR"]:
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.pipeline_registers["DF/DS"]["ALUout_LMD"]

            if operation == "J":
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = instruction["operands"][0]

        # DF Stage
        if self.pipeline["DF"]["operation"] != "NOP":
            instruction = self.pipeline["DF"]
            operation = instruction["operation"]

            if operation == "LW":
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = address

            elif operation == "SW":
                #Check to see if forwarding is needed
                if (instruction["string"] in self.forwarding_detected) and (instruction["operands"][0] == self.pipeline["DS"]["operands"][0]):
                        self.forwarding_counts["DF/DS -> EX/DF"] += 1
                        address = self.pipeline_registers["EX/DF"]["ALUout"]
                        self.pipeline_registers["DF/DS"]["ALUout_LMD"] = address
                        self.pipeline_registers["DF/DS"]["ALUout_LMD_B"] = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["DF/DS -> EX/DF"] = f"({src_string}) to ({instruction['string']})"
                        
                else:
                    address = self.pipeline_registers["EX/DF"]["ALUout"]
                    self.pipeline_registers["DF/DS"]["ALUout_LMD"] = address
                    value = self.registers[instruction["operands"][0]]
                    self.pipeline_registers["DF/DS"]["ALUout_LMD_B"] = value

            elif operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = self.pipeline_registers["EX/DF"]["ALUout"]

            elif operation in ["BEQ", "BNE", "BLT", "BGE", "JAL", "JALR"]:
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = self.pipeline_registers["EX/DF"]["ALUout"]

            elif operation == "J":
                self.pc = self.pipeline_registers["EX/DF"]["ALUout"]
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = 0
                self.pipeline_registers["DF/DS"]["ALUout_LMD_B"] = 0
                self.pipeline_registers["EX/DF"]["ALUout"] = 0
                self.pipeline_registers["EX/DF"]["B"] = 0
                self.pipeline_registers["RF/EX"]["A"] = 0
                self.pipeline_registers["RF/EX"]["B"] = 0
                self.pipeline["IS"] = {"operation": "NOP", "operands": [], "address": None, "string": "** STALL **"}
                self.pipeline["ID"] = {"operation": "NOP", "operands": [None, None, None], "address": None, "string": "** STALL **"}
                self.pipeline["RF"] = {"operation": "NOP", "operands": [None, None, None], "address": None, "string": "** STALL **"}
                self.pipeline["EX"] = {"operation": "NOP", "operands": [None, None, None], "address": None, "string": "** STALL **"}
                self.pipeline_registers["IF/IS"]["NPC"] = self.pc + 4
                self.branch_stalls += 4


        # EX Stage - Execute ALU operations
        if self.pipeline["EX"]["operation"] != "NOP":
            instruction = self.pipeline["EX"]
            operation = instruction["operation"]
            operands = instruction["operands"]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                if "I" in operation:
                    if (instruction["string"] in self.forwarding_detected) and (operands[1] == self.pipeline["DF"]["operands"][0]):
                        self.forwarding_counts["EX/DF -> RF/EX"] += 1
                        src1_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                        src2_value = self.pipeline_registers["RF/EX"]["B"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                        del self.forwarding_detected[instruction["string"]]
                    elif (instruction["string"] in self.forwarding_detected) and (operands[1] == self.pipeline["WB"]["operands"][0]):
                        self.forwarding_counts["DS/WB -> RF/EX"] += 1
                        src1_value = self.registers[operands[1]]
                        src2_value = self.pipeline_registers["RF/EX"]["B"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["DS/WB -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                        del self.forwarding_detected[instruction["string"]]
                    else:
                        src1_value = self.pipeline_registers["RF/EX"]["A"]
                        src2_value = self.pipeline_registers["RF/EX"]["B"]
                else:
                    if (instruction["string"] in self.forwarding_detected) and (operands[1] == self.pipeline["DF"]["operands"][0]):
                        self.forwarding_counts["EX/DF -> RF/EX"] += 1
                        src1_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                        src2_value = self.pipeline_registers["RF/EX"]["B"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                        del self.forwarding_detected[instruction["string"]]
                    elif (instruction["string"] in self.forwarding_detected) and (operands[2] == self.pipeline["DF"]["operands"][0]):
                        self.forwarding_counts["EX/DF -> RF/EX"] += 1
                        src1_value = self.pipeline_registers["RF/EX"]["A"]
                        src2_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                        del self.forwarding_detected[instruction["string"]]
                    else:
                        src1_value = self.pipeline_registers["RF/EX"]["A"]
                        src2_value = self.pipeline_registers["RF/EX"]["B"]

                if operation == "ADD":
                    result = src1_value + src2_value
                elif operation == "SUB":
                    result = src1_value - src2_value
                elif operation == "ADDI":
                    immediate = int(operands[2])
                    result = src1_value + immediate
                elif operation == "SLL":
                    result = src1_value << src2_value
                elif operation == "SRL":
                    result = src1_value >> src2_value
                elif operation == "AND":
                    result = src1_value & src2_value
                elif operation == "OR":
                    result = src1_value | src2_value
                elif operation == "XOR":
                    result = src1_value ^ src2_value
                elif operation == "SLT":
                    result = 1 if src1_value < src2_value else 0
                elif operation == "SLTI":
                    result = 1 if src1_value < int(operands[2]) else 0
                self.pipeline_registers["EX/DF"]["ALUout"] = result
                self.pipeline_registers["EX/DF"]["B"] = src2_value

            elif operation == "SW":

                base_operand = operands[1]
                match = re.match(r'.*\((R\d+)\)', base_operand)
                base_reg = match.group(1)
                if (instruction["string"] in self.forwarding_detected) and (base_reg == self.pipeline["DF"]["operands"][0]):
                    self.forwarding_counts["EX/DF -> RF/EX"] += 1
                    base_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                    address = base_value + 600
                    self.pipeline_registers["EX/DF"]["ALUout"] = address
                    self.pipeline_registers["EX/DF"]["B"] = self.registers[operands[0]]
                    src_string = self.forwarding_detected[instruction["string"]][0]
                    self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                    del self.forwarding_detected[instruction["string"]]
                else:
                    base_value = self.pipeline_registers["RF/EX"]["A"]
                    address = base_value + 600
                    self.pipeline_registers["EX/DF"]["ALUout"] = address
                    self.pipeline_registers["EX/DF"]["B"] = self.registers[operands[0]]
            elif operation == "LW":
                base_operand = operands[1]
                match = re.match(r'.*\((R\d+)\)', base_operand)
                base_reg = match.group(1)
                if (instruction["string"] in self.forwarding_detected) and (base_reg == self.pipeline["DF"]["operands"][0]):
                    self.forwarding_counts["EX/DF -> RF/EX"] += 1
                    base_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                    address = base_value + 600
                    self.pipeline_registers["EX/DF"]["ALUout"] = address
                    src_string = self.forwarding_detected[instruction["string"]][0]
                    self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                    del self.forwarding_detected[instruction["string"]]
                    self.pipeline_registers["EX/DF"]["B"] = 0
                else:
                    base_value = self.pipeline_registers["RF/EX"]["A"]
                    address = base_value + 600
                    self.pipeline_registers["EX/DF"]["ALUout"] = address
                    self.pipeline_registers["EX/DF"]["B"] = self.pipeline_registers["RF/EX"]["B"]

            elif operation in ["BEQ", "BNE", "BLT", "BGE"]:

                if (instruction["string"] in self.forwarding_detected) and (operands[0] == self.pipeline["DF"]["operands"][0]):
                    self.forwarding_counts["EX/DF -> RF/EX"] += 1
                    src1_value = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                    src2_value = self.pipeline_registers["RF/EX"]["B"]
                    src_string = self.forwarding_detected[instruction["string"]][0]
                    self.forwarding_print["EX/DF -> RF/EX"] = f"({src_string}) to ({instruction['string']})"
                    del self.forwarding_detected[instruction["string"]]
                else:
                    src1_value = self.pipeline_registers["RF/EX"]["A"]
                    src2_value = self.pipeline_registers["RF/EX"]["B"]

                branch_taken = False
                if operation == "BEQ" and src1_value == src2_value:
                    branch_taken = True
                elif operation == "BNE" and src1_value != src2_value:
                    branch_taken = True
                elif operation == "BLT" and src1_value < src2_value:
                    branch_taken = True
                elif operation == "BGE" and src1_value >= src2_value:
                    branch_taken = True

                self.pipeline_registers["EX/DF"]["B"] = self.pipeline_registers["RF/EX"]["B"]
                self.pipeline_registers["EX/DF"]["ALUout"] = 556
                if branch_taken:
                    offset = int(operands[2])  
                    self.pc = self.pc + offset
                    self.is_pipeline_complete = True

            elif operation in ["J", "JAL", "JALR"]:
                if operation == "JAL":
                    offset = int(operands[1])
                    self.registers[operands[0]] = self.pc + 4  
                    self.pc = self.pc + offset
                elif operation == "JALR":
                    base_value = self.pipeline_registers["RF/EX"]["A"]
                    self.registers[operands[0]] = self.pc + 4  
                    self.pc = base_value + int(operands[1])
                elif operation == "J":
                    self.pipeline_registers["EX/DF"]["ALUout"] = int(operands[0])
                    self.pipeline_registers["EX/DF"]["B"] = 0
        else:
            self.pipeline_registers["EX/DF"]["ALUout"] = 0
            self.pipeline_registers["EX/DF"]["B"] = 0


        if self.pipeline["RF"]["operation"] != "NOP" and not self.stall_flag:
            instruction = self.pipeline["RF"]
            operation = instruction["operation"]
            operands = instruction["operands"]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                # te first operand is always the destination register, the second is the source register.
                src1 = operands[1]  
                self.pipeline_registers["RF/EX"]["A"] = self.registers[src1]

                if operation in ["ADD", "SUB", "SLL", "SRL", "AND", "OR", "XOR", "SLT"]:
                    if len(operands) > 2:
                        src2 = operands[2] 
                        if src2.startswith('R'):
                            self.pipeline_registers["RF/EX"]["B"] = self.registers[src2]
                        else:
                            self.pipeline_registers["RF/EX"]["B"] = int(src2)

            elif operation in ["SW", "LW"]:
                base_operand = operands[1]  
                match = re.match(r'.*\((R\d+)\)', base_operand)
                base_reg = match.group(1) 

                self.pipeline_registers["RF/EX"]["A"] = self.registers[base_reg]
                if operation == "SW":
                    # For SW also need the value to be stored, operand[1]
                    src_value = operands[0]
                    self.pipeline_registers["RF/EX"]["B"] = self.registers[src_value]
                if operation == "LW":
                    just_stalled = False
                    if len(self.pipeline["ID"]["operands"]) > 2:
                        if operands[0] == self.pipeline["ID"]["operands"][1] or operands[0] == self.pipeline["ID"]["operands"][2]:
                            self.stall_counter += 2
                            just_stalled = True
                    if not just_stalled and operands[0] == self.pipeline["ID"]["operands"][1]:
                        self.stall_counter += 2
                        just_stalled = True
                    if not just_stalled and len(self.pipeline["IS"]["operands"]) > 2:
                        if operands[0] == self.pipeline["IS"]["operands"][1] or operands[0] == self.pipeline["IS"]["operands"][2]:
                            self.stall_counter += 1
                            just_stalled = True
                    if not just_stalled and operands[0] == self.pipeline["IS"]["operands"][1]:
                        self.stall_counter += 1
                        just_stalled = True

            elif operation == "BEQ":
                self.pipeline_registers["RF/EX"]["A"] = self.registers[operands[0]]
                self.pipeline_registers["RF/EX"]["B"] = self.registers[operands[1]]
            elif operation == "J":
                self.pipeline_registers["RF/EX"]["A"] = 0
                self.pipeline_registers["RF/EX"]["B"] = 0


        # ID Stage - Decode Instruction
        if self.pipeline["ID"]["operation"] != "NOP" and not self.stall_flag:
            instruction_in_id = self.pipeline["ID"]

            operation = instruction_in_id["operation"]
            operands = instruction_in_id["operands"]
            src1 = None
            src2 = None

            if operation in ["SW"]:
                src1 = operands[0]
                match = re.match(r'.*\((R\d+)\)', operands[1])
                src2 = match.group(1)
            elif operation in ["LW"]:
                match = re.match(r'.*\((R\d+)\)', operands[1])
                src1 = match.group(1)
                src2 = None
            elif operation in ["BEQ", "BNE", "BLT", "BGE"]:
                src1 = operands[0]
                src2 = operands[1]
            else:
                # identify sources
                src1 = operands[1] if len(operands) > 1 and operands[1].startswith('R') else None
                src2 = operands[2] if len(operands) > 2 and operands[2].startswith('R') else None

            for stage in ["RF", "EX", "DF"]:
                if self.pipeline[stage]["operation"] != "NOP":
                    producing_instruction = self.pipeline[stage]
                    dest_reg = producing_instruction["operands"][0] if producing_instruction["operands"] else None
                    if producing_instruction["operation"] == "SW":
                        dest_reg = None

                    # RAW hazard check
                    if dest_reg and (src1 == dest_reg or src2 == dest_reg):
                        if instruction_in_id["string"] not in self.forwarding_detected:
                            self.forwarding_detected[instruction_in_id["string"]] = []
                        if producing_instruction["string"] not in self.forwarding_detected[instruction_in_id["string"]]:
                            self.forwarding_detected[instruction_in_id["string"]].append(producing_instruction["string"])


        # IS Stage
        # Update IR register in IS/ID pipeline register
        if self.pipeline["IS"] != {"operation": "NOP", "operands": [], "address": None} and not self.stall_flag:
            self.pipeline_registers["IS/ID"]["IR"] = self.pipeline["IS"]

        # IF Stage
        if self.pc < 496 + len(self.instructions) * 4 and not self.stall_flag:
            next_instruction_index = (self.pc - 496) // 4
            self.pipeline["IF"] = self.parse_instruction(self.instructions[next_instruction_index])
            self.pipeline_registers["IF/IS"]["NPC"] = self.pc + 4
        elif not self.stall_flag:
            self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}

        self.print_pipeline_trace()

        self.forwarding_print = {        #This just for resetting forwarding printouts after each iteration
            "EX/DF -> RF/EX": "",
            "DF/DS -> EX/DF": "",
            "DF/DS -> RF/EX": "",
            "DS/WB -> EX/DF": "",
            "DS/WB -> RF/EX": ""
        }
        if self.stall_counter == 0:
            self.pc += 4


        if all(stage["operation"] == "NOP" for stage in self.pipeline.values()):
            self.is_pipeline_complete = True


    def print_pipeline_trace(self):
        if (self.trace_start is None and self.trace_end is None) or \
        (self.trace_start <= self.clock_cycle <= self.trace_end):
            to_print = []
            to_print.append(f"***** Cycle #{self.clock_cycle}***********************************************")
            to_print.append(f"Current PC = {self.pc}:")
            to_print.append("Pipeline Status:")
            for stage, instr in self.pipeline.items():
                operation = "<unknown>" if stage == "IF" else instr["string"]
                to_print.append(f"* {stage} : {operation}")
            to_print.append(" ")
            stall_instr = self.pipeline["ID"] if self.pipeline["ID"] == "** STALL **" else "(none)"
            to_print.append(f"Stall Instruction: {stall_instr}\n")

            to_print.append("Forwarding:")
            if self.pipeline["ID"]["operation"] != "NOP" and not self.stall_flag:
                current_instruction = self.pipeline["ID"]["string"]
                detected_forwarding = [
                    f"({src_string}) to ({current_instruction})"
                    for src_string in self.forwarding_detected.get(current_instruction, [])
                ]
                lw_not_detected = True
                for src_string in self.forwarding_detected.get(current_instruction, []):
                    if "LW" in src_string:
                        lw_not_detected = False
                if detected_forwarding and lw_not_detected:
                    to_print.append(" Detected: ")
                    for forward in detected_forwarding:
                        to_print.append(f"\t{forward}")
                else:
                    to_print.append(" Detected: (none)")
            else:
                to_print.append(" Detected: (none)")

            to_print.append(" Forwarded:")
            for path, count in self.forwarding_print.items():
                to_print.append(f" * {path} : {count}")
            to_print.append(" ")

            to_print.append("Pipeline Registers:")
            for reg, values in self.pipeline_registers.items():
                if not reg == "DF/DS":
                    for key, value in values.items():
                        to_print.append(f"* {reg}.{key}\t: {value}")
            to_print.append(" ")

            to_print.append("Integer registers:")
            for i in range(0, 32, 4):
                to_print.append(f"R{i}\t{self.registers[f'R{i}']}\tR{i+1}\t{self.registers[f'R{i+1}']}\tR{i+2}\t{self.registers[f'R{i+2}']}\tR{i+3}\t{self.registers[f'R{i+3}']}")
            to_print.append(" ")

            to_print.append("Data memory:")
            for addr in range(600, 640, 4):
                to_print.append(f"{addr}: {self.memory.get(addr, 0)}")
            to_print.append(" ")

            to_print.append("Total Stalls:")
            to_print.append(f"*Loads\t: {self.load_stalls}")
            to_print.append(f"*Branches: {self.branch_stalls}")
            to_print.append(f"*Other\t: {self.other_stalls}\n")

            to_print.append("Total Forwardings:")
            for path, count in self.forwarding_counts.items():
                to_print.append(f" * {path} : {count}")
            to_print.append(" ")

            if self.output_file_name_2:
                with open(self.output_file_name_2, 'a') as file:
                    file.write("\n".join(to_print) + "\n")

            print("\n".join(to_print))

    def print_final_summary(self):
        summary_lines = []
        summary_lines.append("\nFinal Simulation Summary:")
        summary_lines.append(f"Total Cycles: {self.clock_cycle}")
        self.total_stalls = self.load_stalls + self.branch_stalls
        summary_lines.append(f"Total Stalls: {self.total_stalls}")
        summary_lines.append(f"  Load Stalls: {self.load_stalls}")
        summary_lines.append(f"  Branch Stalls: {self.branch_stalls}")
        summary_lines.append(f"  Other Stalls: {self.other_stalls}")
        self.total_forwardings = sum(self.forwarding_counts.values())
        summary_lines.append(f"Total Forwardings: {self.total_forwardings}")
        summary_lines.append(" ")

        summary_lines.append("\nRegisters:")
        for reg, value in self.registers.items():
            summary_lines.append(f"  {reg}: {value}")
        summary_lines.append(" ")

        summary_lines.append("\nMemory:")
        for addr in range(600, 640, 4):
            summary_lines.append(f"  {addr}: {self.memory[addr]}")
        summary_lines.append(" ")

        if self.output_file_name_2:
            with open(self.output_file_name_2, 'a') as file:
                file.write("\n".join(summary_lines) + "\n")
        print("\n".join(summary_lines))
