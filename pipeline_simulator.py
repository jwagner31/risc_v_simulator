# pipeline_simulator.py
import re

class PipelineSimulator:
    def __init__(self, instructions, trace_start=None, trace_end=None):
        # Input list of decoded instructions from disassembler
        self.instructions = self.convert_instructions(instructions)  # List of disassembled instructions to be simulated
        # Initialize pipeline as a dictionary with stages as keys
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
        self.clock_cycle = 0              # Track the number of clock cycles
        self.trace_start = trace_start    # Start of tracing cycle
        self.trace_end = trace_end        # End of tracing cycle

        # Register and Memory Setup
        self.registers = {f"R{i}": 0 for i in range(32)}  # 32 general-purpose registers as a dictionary
        self.memory = {i: 0 for i in range(600, 640, 4)}    # Dictionary to represent memory space from address 600 to 636

        # Metrics for logging simulation performance
        self.total_stalls = 0             # Total number of stalls
        self.total_forwardings = 0        # Total number of forwardings
        self.load_stalls = 0              # Load stalls
        self.branch_stalls = 0            # Branch stalls
        self.other_stalls = 0             # Other stalls
        
        # Forwarding counts and detection

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
        
        # Pipeline registers setup
        self.pipeline_registers = {
            "IF/IS": {"NPC": 0},
            "IS/ID": {"IR": nop_instruction},
            "RF/EX": {"A": 0, "B": 0},
            "EX/DF": {"ALUout": 0, "B": 0},
            "DF/DS": {"ALUout_LMD": 0, "ALUout_LMD_B": 0},
            "DS/WB": {"ALUout_LMD": 0}
        }
        
        # Flag to indicate the pipeline's completion state
        self.is_pipeline_complete = False

        # Program Counter
        self.pc = 496
        self.stall_counter = 0

    def simulate(self):
        # Entry point for running the pipeline simulation
        for i in range(self.trace_end):
            self.advance_pipeline()       # Move instructions through the pipeline stages
            self.clock_cycle += 1         # Increment clock cycle count
        
        # Print final state and statistics
        #self.print_final_summary()

    def convert_instructions(self, instruction_lines):
        formatted_instructions = []

        for line in instruction_lines:
            # Replace all tab characters with spaces
            formatted_line = line.replace('\t', ' ')
            
            # Append the formatted line to the list of formatted instructions
            formatted_instructions.append(formatted_line)
        
        return formatted_instructions
    
    def parse_instruction(self, instruction):
        # Parse the given instruction string and return a dictionary of components
        # Instructions are formatted as: assembly representation followed by address
        parts = instruction.split()
        asm_str = ""
        for i in range(7, len(parts)):
            asm_str += parts[i] + " "
        address = int(parts[6])  # Address as integer
        # Split asm_str into operation and operands
        operation = parts[7]  # Operation name (e.g., ADDI, SW, LW)
        operands = [op.replace('x', 'R').replace(',', '') for op in parts[8:]]  # Replace 'x' with 'R' for consistency and remove commas

        # Construct parsed instruction dictionary
        parsed_instr = {
            "string": asm_str,
            "operation": operation,
            "operands": operands,
            "address": address
        }
        return parsed_instr

    def advance_pipeline(self):

        # advance pipeline 
        self.pipeline["WB"] = self.pipeline["DS"]
        self.pipeline["DS"] = self.pipeline["DF"]
        self.pipeline["DF"] = self.pipeline["EX"]
        self.pipeline["EX"] = self.pipeline["RF"]
        self.pipeline["RF"] = self.pipeline["ID"]
        self.pipeline["ID"] = self.pipeline["IS"]
        self.pipeline["IS"] = self.pipeline["IF"]
        self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}  # Reset IF stage to NOP

        # WB Stage - Write Back to registers
        if self.pipeline["WB"]["operation"] != "NOP":
            instruction = self.pipeline["WB"]
            if instruction["operation"] in ["LW", "ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                dest_reg = instruction["operands"][0]
                result = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                self.registers[dest_reg] = result

        # DS Stage
        if self.pipeline["DS"]["operation"] != "NOP":
            instruction = self.pipeline["DS"]
            operation = instruction["operation"]

            # Flush the instruction entry out the forwarding dictionary, since we are past any necessary forwarding
            if instruction["string"] in self.forwarding_detected:
                del self.forwarding_detected[instruction["string"]]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                # For arithmetic and logical instructions, pass ALU result to ALUout_LMD
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
            elif operation in ["SW"]:
                # need to store the value currently in the 
                address = self.pipeline_registers["DF/DS"]["ALUout_LMD"]
                value = self.pipeline_registers["DF/DS"]["ALUout_LMD_B"]
                self.memory[address] = value

            elif operation in ["LW"]:
                # For LW and SW, no value to propagate; ensure ALUout_LMD is cleared
                pass
            elif operation in ["BEQ", "BNE", "BLT", "BGE", "JAL", "JALR"]:
                # For branch and jump instructions, no value to propagate; ensure ALUout_LMD is cleared
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = 0

        # DF Stage
        if self.pipeline["DF"]["operation"] != "NOP":
            instruction = self.pipeline["DF"]
            operation = instruction["operation"]

            if operation == "LW":
                # For LW, read from memory and store in ALUout_LMD
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = self.memory[address]

            elif operation == "SW":
                #Check to see if forwarding is needed
                if instruction["string"] in self.forwarding_detected:
                    if instruction["operands"][0] == self.pipeline["DS"]["operands"][0]:
                        self.forwarding_counts["DF/DS -> EX/DF"] += 1
                        address = self.pipeline_registers["EX/DF"]["ALUout"]
                        self.pipeline_registers["DF/DS"]["ALUout_LMD"] = address
                        self.pipeline_registers["DF/DS"]["ALUout_LMD_B"] = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                        src_string = self.forwarding_detected[instruction["string"]][0]
                        self.forwarding_print["DF/DS -> EX/DF"] = f"({src_string}) to ({instruction['string']})"
                        
                else:
                    # SW passes along value
                    address = self.pipeline_registers["EX/DF"]["ALUout"]
                    self.pipeline_registers["DF/DS"]["ALUout_LMD"] = address
                    value = self.pipeline_registers["EX/DF"]["B"]
                    self.pipeline_registers["DF/DS"]["ALUout_LMD_B"] = value
                    #self.memory[address] = value

            elif operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                # For arithmetic and logical instructions, pass ALU result to ALUout_LMD
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = self.pipeline_registers["EX/DF"]["ALUout"]

            elif operation in ["BEQ", "BNE", "BLT", "BGE", "JAL", "JALR"]:
                # For branch and jump instructions, no value to propagate; ensure ALUout_LMD is cleared
                self.pipeline_registers["DF/DS"]["ALUout_LMD"] = 0

        # EX Stage - Execute ALU operations
        # EX Stage - Execute ALU operations
        if self.pipeline["EX"]["operation"] != "NOP":
            instruction = self.pipeline["EX"]
            operation = instruction["operation"]
            operands = instruction["operands"]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
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

                if instruction["string"] in self.forwarding_detected:
                    base_operand = operands[1]
                    match = re.match(r'.*\((R\d+)\)', base_operand)
                    base_reg = match.group(1)


                # For SW, the address is calculated based on the base register value and the offset (which is always 600)
                base_value = self.pipeline_registers["RF/EX"]["A"]
                address = base_value + 600
                self.pipeline_registers["EX/DF"]["ALUout"] = address
                #self.pipeline_registers["EX/DF"]["B"] = self.pipeline_registers["RF/EX"]["B"]
                self.pipeline_registers["EX/DF"]["B"] = self.registers[operands[0]]

            elif operation == "LW":
                # For LW, the address is calculated similarly
                base_value = self.pipeline_registers["RF/EX"]["A"]
                address = base_value + 600
                self.pipeline_registers["EX/DF"]["ALUout"] = address
                self.pipeline_registers["EX/DF"]["B"] = self.pipeline_registers["RF/EX"]["B"]

            elif operation in ["BEQ", "BNE", "BLT", "BGE"]:
                # Branch operations
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

                if branch_taken:
                    offset = int(operands[2])  # Branch offset
                    self.pc = self.pc + offset
                    self.branch_stalls += 1
                    # Invalidate pipeline stages to insert bubbles
                    self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None, "string": "NOP"}
                    self.pipeline["IS"] = {"operation": "NOP", "operands": [], "address": None, "string": "NOP"}
                    self.pipeline["ID"] = {"operation": "NOP", "operands": [], "address": None, "string": "NOP"}

            elif operation in ["JAL", "JALR"]:
                # Jump and link operations
                if operation == "JAL":
                    offset = int(operands[1])
                    self.registers[operands[0]] = self.pc + 4  # Store return address
                    self.pc = self.pc + offset
                elif operation == "JALR":
                    base_value = self.pipeline_registers["RF/EX"]["A"]
                    self.registers[operands[0]] = self.pc + 4  # Store return address
                    self.pc = base_value + int(operands[1])
        else:
            # No operation in EX stage; clear out registers 
            self.pipeline_registers["EX/DF"]["ALUout"] = 0
            self.pipeline_registers["EX/DF"]["B"] = 0


        if self.pipeline["RF"]["operation"] != "NOP":
            instruction = self.pipeline["RF"]
            operation = instruction["operation"]
            operands = instruction["operands"]

            if operation in ["ADD", "SUB", "ADDI", "SLL", "SRL", "AND", "OR", "XOR", "SLT", "SLTI"]:
                # The first operand is always the destination register, the second is the source register.
                src1 = operands[1]  # Get the source register for these types of instructions
                self.pipeline_registers["RF/EX"]["A"] = self.registers[src1]

                # Some instructions have a second source operand (register or immediate)
                if operation in ["ADD", "SUB", "SLL", "SRL", "AND", "OR", "XOR", "SLT"]:
                    if len(operands) > 2:
                        src2 = operands[2]  # Get the second source register or immediate value
                        if src2.startswith('R'):
                            self.pipeline_registers["RF/EX"]["B"] = self.registers[src2]
                        else:
                            self.pipeline_registers["RF/EX"]["B"] = int(src2)

            elif operation in ["SW", "LW"]:
                # For LW and SW, we need to extract the base register from the memory address operand
                base_operand = operands[1]  # This would be something like "600(R0)"
                
                match = re.match(r'.*\((R\d+)\)', base_operand)
                base_reg = match.group(1)  # Extract base register (e.g., "R0")

                # Set the pipeline registers
                self.pipeline_registers["RF/EX"]["A"] = self.registers[base_reg]
                if operation == "SW":
                    # For SW, we also need the value to be stored, which is the first operand (a register)
                    src_value = operands[0]  # Value to be stored (e.g., "R6")
                    self.pipeline_registers["RF/EX"]["B"] = self.registers[src_value]

        # ID Stage - Decode Instruction
        if self.pipeline["ID"]["operation"] != "NOP":
            instruction_in_id = self.pipeline["ID"]

            operation = instruction_in_id["operation"]
            operands = instruction_in_id["operands"]
            src1 = None
            src2 = None

            if operation in ["SW"]:
                src1 = operands[0]
                match = re.match(r'.*\((R\d+)\)', operands[1])
                src2 = match.group(1)  # Extract base register (e.g., "R0") 
            elif operation in ["LW"]:
                match = re.match(r'.*\((R\d+)\)', operands[1])
                src1 = match.group(1)
                src2 = None
            else:
                # Identify source registers for the current instruction
                src1 = operands[1] if len(operands) > 1 and operands[1].startswith('R') else None
                src2 = operands[2] if len(operands) > 2 and operands[2].startswith('R') else None
            
            print()
            # print the instruction in ID stage and the source registers
            #print(f"Instruction in ID: {instruction_in_id}")
            #print(f"Source Registers: {src1}, {src2}")

            # Iterate over relevant pipeline stages to check for dependencies
            for stage in ["RF", "EX", "DF"]:
                if self.pipeline[stage]["operation"] != "NOP":
                    producing_instruction = self.pipeline[stage]
                    dest_reg = producing_instruction["operands"][0] if producing_instruction["operands"] else None
                    if producing_instruction["operation"] == "SW":
                        dest_reg = None

                    # Check if there is a RAW hazard
                    if dest_reg and (src1 == dest_reg or src2 == dest_reg):
                        if instruction_in_id["string"] not in self.forwarding_detected:
                            self.forwarding_detected[instruction_in_id["string"]] = []
                        if producing_instruction["string"] not in self.forwarding_detected[instruction_in_id["string"]]:
                            self.forwarding_detected[instruction_in_id["string"]].append(producing_instruction["string"])


        # IS Stage - Continue instruction fetch from IF stage
        # Update IR register in IS/ID pipeline register
        if self.pipeline["IS"] != {"operation": "NOP", "operands": [], "address": None}:
            self.pipeline_registers["IS/ID"]["IR"] = self.pipeline["IS"]

        # IF Stage - Fetch next instruction
        if self.pc < 496 + len(self.instructions) * 4:
            next_instruction_index = (self.pc - 496) // 4
            self.pipeline["IF"] = self.parse_instruction(self.instructions[next_instruction_index])
            self.pipeline_registers["IF/IS"]["NPC"] = self.pc + 4
        else:
            self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}  # No more instructions to fetch

        self.print_pipeline_trace()
        self.forwarding_print = {
            "EX/DF -> RF/EX": "",
            "DF/DS -> EX/DF": "",
            "DF/DS -> RF/EX": "",
            "DS/WB -> EX/DF": "",
            "DS/WB -> RF/EX": ""
        }

        self.pc += 4


        # Check if the pipeline is complete (all stages are NOP)
        if all(stage["operation"] == "NOP" for stage in self.pipeline.values()):
            self.is_pipeline_complete = True


    def print_pipeline_trace(self):
        # Print the current state of the pipeline for tracing purposes (if within trace range)
        if (self.trace_start is None and self.trace_end is None) or \
           (self.trace_start <= self.clock_cycle <= self.trace_end):
            print(f"***** Cycle #{self.clock_cycle}***********************************************")
            print(f"Current PC = {self.pc}:")

            # Pipeline Status
            print("Pipeline Status:")
            for stage, instr in self.pipeline.items():
                if stage == "IF":
                    operation = "<unknown>"
                operation = instr["string"]
                print(f"* {stage} : {operation}")
            print()
                        # Stall Instruction
            stall_instr = self.pipeline["ID"] if self.pipeline["ID"] == "** STALL **" else "(none)"
            print(f"Stall Instruction: {stall_instr}\n")

            print("Forwarding:")
            if self.pipeline["ID"]["operation"] != "NOP":
                current_instruction = self.pipeline["ID"]["string"]
                detected_forwarding = [
                    f"({src_string}) to ({current_instruction})"
                    for src_string in self.forwarding_detected.get(current_instruction, [])
                ]
                if detected_forwarding:
                    print(" Detected: ")
                    for forward in detected_forwarding:
                        print(f"\t{forward}")
                else:
                    print(" Detected: (none)")
            else:
                print(" Detected: (none)")

            print(" Forwarded:")
            for path, count in self.forwarding_print.items():
                print(f" * {path} : {count}")
            print()

            # Pipeline Registers
            print("Pipeline Registers:")
            for reg, values in self.pipeline_registers.items():
                for key, value in values.items():
                    print(f"* {reg}.{key}\t: {value}")
            print()

            # Integer Registers
            print("Integer registers:")
            for i in range(0, 32, 4):
                print(f"R{i}\t{self.registers[f'R{i}']}\tR{i+1}\t{self.registers[f'R{i+1}']}\tR{i+2}\t{self.registers[f'R{i+2}']}\tR{i+3}\t{self.registers[f'R{i+3}']}")
            print()

            # Data Memory
            print("Data memory:")
            for addr in range(600, 640, 4):
                print(f"{addr}: {self.memory.get(addr, 0)}")
            print()

            # Total Stalls
            print("Total Stalls:")
            print(f"*Loads\t: {self.load_stalls}")
            print(f"*Branches: {self.branch_stalls}")
            print(f"*Other\t: {self.other_stalls}\n")

            # Total Forwardings
            print("Total Forwardings:")
            for path, count in self.forwarding_counts.items():
                print(f" * {path} : {count}")
            print()

    def print_final_summary(self):
        # Print final summary after pipeline simulation completes
        print("\nFinal Simulation Summary:")
        print(f"Total Cycles: {self.clock_cycle}")
        print(f"Total Stalls: {self.total_stalls}")
        print(f"  Load Stalls: {self.load_stalls}")
        print(f"  Branch Stalls: {self.branch_stalls}")
        print(f"  Other Stalls: {self.other_stalls}")
        print(f"Total Forwardings: {self.total_forwardings}")

        # Print register contents
        print("\nRegisters:")
        for reg, value in self.registers.items():
            print(f"  {reg}: {value}")

        # Print memory contents
        print("\nMemory:")
        for addr in range(600, 640, 4):
            print(f"  {addr}: {self.memory[addr]}")
