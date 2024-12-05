import argparse
from pipeline_simulator import PipelineSimulator
from disassembler import Disassembler

def main():
    # Command line args
    parser = argparse.ArgumentParser(description="RISC-V Simulator")
    parser.add_argument("input_file_name", help="Input file containing binary instructions")
    parser.add_argument("output_file_name", help="Output file to write results")
    parser.add_argument('oper', choices=['dis', 'sim'], help="Operation to perform: disassembly or simulation")
    parser.add_argument('-T', metavar="m:n", type=str, help="Trace mode - start (m) and end (n) cycles")

    args = parser.parse_args()

    if args.oper == 'dis':
        # Since disassembly functionality isn't our focus right now, I am just keeping a placeholder.
        # Assuming the disassembler writes directly to the output_file.
        disassembler = Disassembler(args.input_file_name, args.output_file_name)
        disassembler.disassemble()

    elif args.oper == 'sim':
        # Pass parsed trace argument if available
        if args.T:
            try:
                trace_start, trace_end = map(int, args.T.split(":"))
            except ValueError:
                print("Invalid format for trace argument. Use -T m:n.")
                return
        else:
            trace_start, trace_end = None, None  # Default - trace everything

        # Read the instructions from the output file
        with open(args.output_file_name, 'r') as file:
            instructions = file.readlines()

        # Process instructions to format them correctly for PipelineSimulator
        instructions = [instr.strip() for instr in instructions if instr.strip() != '']

        # Create and run the Pipeline Simulator
        pipeline_sim = PipelineSimulator(instructions, trace_start, trace_end)
        pipeline_sim.simulate()

    else:
        print("Invalid operation.")

if __name__ == "__main__":
    main()
