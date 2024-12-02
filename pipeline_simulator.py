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
        self.registers = {f"x{i}": 0 for i in range(32)}  # 32 general-purpose registers as a dictionary
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
            "IS/ID": {"IR": 0},
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

    def advance_pipeline(self):
        # Method to move instructions through the pipeline stages
        # Placeholder for future implementation
        pass

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
                print(f"* {stage} : {instr}")
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
                print(f"R{i}\t{self.registers[f'x{i}']}\tR{i+1}\t{self.registers[f'x{i+1}']}\tR{i+2}\t{self.registers[f'x{i+2}']}\tR{i+3}\t{self.registers[f'x{i+3}']}")
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
        for addr, value in sorted(self.memory.items()):
            print(f"  Address {addr}: {value}")
