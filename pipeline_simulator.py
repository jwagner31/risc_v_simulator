# pipeline_simulator.py
import re

class PipelineSimulator:
    def __init__(self, instructions, trace_start=None, trace_end=None):
        # Input list of decoded instructions from disassembler
        self.instructions = self.convert_instructions(instructions)  # List of disassembled instructions to be simulated
        #print(self.instructions)
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
        self.forwarding_detected = []  # List to keep track of forwarding detections for each cycle
        
        # Pipeline registers setup
        self.pipeline_registers = {
            "IF/IS": {"NPC": 0},
            "IS/ID": {"IR": nop_instruction},
            "RF/EX": {"A": 0, "B": 0},
            "EX/DF": {"ALUout": 0, "B": 0},
            "DS/WB": {"ALUout_LMD": 0}
        }
        
        # Flag to indicate the pipeline's completion state
        self.is_pipeline_complete = False

        # Program Counter
        self.pc = 496

    def simulate(self):
        # Entry point for running the pipeline simulation
        for i in range(self.trace_end):
            self.detect_hazards()         # Detect hazards and insert stalls if necessary
            self.advance_pipeline()       # Move instructions through the pipeline stages
            #self.print_pipeline_trace()   # Print the trace information (if enabled)
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
        # print the length of isntructions
        #print(len(instruction))
        #print(parts)
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

        # Advance pipeline by shifting all stages (from WB to IF)
        self.pipeline["WB"] = self.pipeline["DS"]
        self.pipeline["DS"] = self.pipeline["DF"]
        self.pipeline["DF"] = self.pipeline["EX"]
        self.pipeline["EX"] = self.pipeline["RF"]
        self.pipeline["RF"] = self.pipeline["ID"]
        self.pipeline["ID"] = self.pipeline["IS"]
        self.pipeline["IS"] = self.pipeline["IF"]
        self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}  # Reset IF stage to NOP

        # WB Stage - Write Back to registers
        
        ''' 
        if self.pipeline["WB"]["operation"] != "NOP":
            instruction = self.pipeline["WB"]
            if instruction["operation"] in ["LW", "ADD", "SUB", "ADDI"]:
                dest_reg = instruction["operands"][0]
                result = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                self.registers[dest_reg] = result

        # DS Stage - Complete data memory access
        if self.pipeline["DS"]["operation"] != "NOP":
            instruction = self.pipeline["DS"]
            if instruction["operation"] == "LW":
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.memory[address]
            elif instruction["operation"] == "SW":
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                value = self.pipeline_registers["EX/DF"]["B"]
                self.memory[address] = value

        # EX Stage - Execute ALU operations
        if self.pipeline["EX"]["operation"] != "NOP":
            instruction = self.pipeline["EX"]
            if instruction["operation"] in ["ADD", "SUB", "ADDI"]:
                src1 = instruction["operands"][1]
                src2 = instruction["operands"][2] if len(instruction["operands"]) > 2 else None
                if instruction["operation"] == "ADD":
                    result = self.registers[src1] + self.registers[src2]
                elif instruction["operation"] == "SUB":
                    result = self.registers[src1] - self.registers[src2]
                elif instruction["operation"] == "ADDI":
                    result = self.registers[src1] + int(src2)
                self.pipeline_registers["EX/DF"]["ALUout"] = result
        

        '''
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
        # For simplicity, assume ID just passes the instruction to RF, hazard detection will be implemented here.

        # IS Stage - Continue instruction fetch from IF stage

        # IF Stage - Fetch next instruction
        if self.pc < 496 + len(self.instructions) * 4:
            next_instruction_index = (self.pc - 496) // 4
            print(next_instruction_index)
            self.pipeline["IF"] = self.parse_instruction(self.instructions[next_instruction_index])
            self.pipeline_registers["IF/IS"]["NPC"] = self.pc + 4
        else:
            self.pipeline["IF"] = {"operation": "NOP", "operands": [], "address": None}  # No more instructions to fetch

        self.print_pipeline_trace()
        self.pc += 4


        # Check if the pipeline is complete (all stages are NOP)
        if all(stage["operation"] == "NOP" for stage in self.pipeline.values()):
            self.is_pipeline_complete = True


    def detect_hazards(self):
        # Method to detect hazards and insert stalls as needed
        # Placeholder for future implementation
        pass

    def apply_forwarding(self):
        # Method to handle forwarding of data between pipeline stages to avoid hazards
        # Placeholder for future implementation
        pass

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

            # Forwarding Information
            detected_forwarding = ", ".join(self.forwarding_detected) if self.forwarding_detected else "(none)"
            print("Forwarding:")
            print(f" Detected: {detected_forwarding}")
            print(" Forwarded:")
            for path, count in self.forwarding_counts.items():
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
