# pipeline_simulator.py

class PipelineSimulator:
    def __init__(self, instructions, trace_start=None, trace_end=None):
        # Input list of decoded instructions from disassembler
        self.instructions = instructions  # List of disassembled instructions to be simulated
        
        # Initialize pipeline as a dictionary with stages as keys
        self.pipeline = {
            "IF": "NOP",
            "IS": "NOP",
            "ID": "NOP",
            "RF": "NOP",
            "EX": "NOP",
            "DF": "NOP",
            "DS": "NOP",
            "WB": "NOP"
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
            "IS/ID": {"IR": "NOP"},
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
        while not self.is_pipeline_complete:
            self.detect_hazards()         # Detect hazards and insert stalls if necessary
            self.advance_pipeline()       # Move instructions through the pipeline stages
            self.print_pipeline_trace()   # Print the trace information (if enabled)
            self.clock_cycle += 1         # Increment clock cycle count
        
        # Print final state and statistics
        self.print_final_summary()

    def parse_instruction(self, instruction):
        # Parse the given instruction string and return a dictionary of components
        # Instructions are formatted as: assembly representation followed by address
        parts = instruction.split('\t')
        asm_str = parts[2]  # Assembly representation
        address = int(parts[1])  # Address as integer
        # Split asm_str into operation and operands
        asm_parts = asm_str.split()
        operation = asm_parts[0]  # Operation name (e.g., ADDI, SW, LW)
        operands = [op.replace('x', 'R').replace(',', '') for op in asm_parts[1:]]  # Replace 'x' with 'R' for consistency and remove commas

        # Construct parsed instruction dictionary
        parsed_instr = {
            "string": asm_str,
            "operation": operation,
            "operands": operands,
            "address": address
        }
        print(parsed_instr)
        return parsed_instr

    def advance_pipeline(self):
        # WB Stage - Write Back to registers
        if self.pipeline["WB"] != "NOP":
            instruction = self.pipeline["WB"]
            if instruction["operation"] in ["LW", "ADD", "SUB", "ADDI"]:
                dest_reg = instruction["operands"][0]
                result = self.pipeline_registers["DS/WB"]["ALUout_LMD"]
                self.registers[dest_reg] = result

        # DS Stage - Complete data memory access
        if self.pipeline["DS"] != "NOP":
            instruction = self.pipeline["DS"]
            if instruction["operation"] == "LW":
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                self.pipeline_registers["DS/WB"]["ALUout_LMD"] = self.memory[address]
            elif instruction["operation"] == "SW":
                address = self.pipeline_registers["EX/DF"]["ALUout"]
                value = self.pipeline_registers["EX/DF"]["B"]
                self.memory[address] = value

        # EX Stage - Execute ALU operations
        if self.pipeline["EX"] != "NOP":
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

        # RF Stage - Fetch registers for next operations
        if self.pipeline["RF"] != "NOP":
            instruction = self.pipeline["RF"]
            if instruction["operation"] in ["ADD", "SUB", "SW", "LW", "ADDI"]:
                src1 = instruction["operands"][1]
                self.pipeline_registers["RF/EX"]["A"] = self.registers[src1]
                if len(instruction["operands"]) > 2:
                    src2 = instruction["operands"][2]
                    self.pipeline_registers["RF/EX"]["B"] = self.registers[src2]

        # ID Stage - Decode Instruction
        # For simplicity, assume ID just passes the instruction to RF, hazard detection will be implemented here.

        # IS Stage - Continue instruction fetch from IF stage

        # IF Stage - Fetch next instruction
        if self.pc < 496 + len(self.instructions) * 4:
            next_instruction_index = (self.pc - 496) // 4
            self.pipeline["IF"] = self.parse_instruction(self.instructions[next_instruction_index])
            self.pc += 4
        else:
            self.pipeline["IF"] = {"operation": "NOP"}  # No more instructions to fetch

        # Advance pipeline by shifting all stages (from WB to IF)
        self.pipeline["WB"] = self.pipeline["DS"]
        self.pipeline["DS"] = self.pipeline["DF"]
        self.pipeline["DF"] = self.pipeline["EX"]
        self.pipeline["EX"] = self.pipeline["RF"]
        self.pipeline["RF"] = self.pipeline["ID"]
        self.pipeline["ID"] = self.pipeline["IS"]
        self.pipeline["IS"] = self.pipeline["IF"]

        # Check if the pipeline is complete (all stages are NOP)
        if all(stage == {"operation": "NOP"} for stage in self.pipeline.values()):
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
                print(f"* {stage} : {instr['operation'] if isinstance(instr, dict) else instr}")
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
