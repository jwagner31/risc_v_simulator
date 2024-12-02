import argparse
from disassembler import Disassembler
from pipeline_simulator import PipelineSimulator

def main():
    # Command line args
    parser = argparse.ArgumentParser(description="RISC-V Simulator")
    parser.add_argument("input_file_name", help="Input file containing binary instructions")
    parser.add_argument("output_file_name", help="Output file to write results")
    parser.add_argument('oper', choices=['dis', 'sim'], help="Operation to perform: disassembly or simulation")
    parser.add_argument('-T', metavar="m:n", type=str, help="Trace mode - start (m) and end (n) cycles")

    args = parser.parse_args()

    if args.oper == 'dis':
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

        # Initialize Disassembler to get the parsed instructions
        disassembler = Disassembler(args.input_file_name, args.output_file_name)
        disassembler.disassemble()

        # Create and run the Pipeline Simulator
        pipeline_sim = PipelineSimulator(disassembler.result, trace_start, trace_end)
        pipeline_sim.simulate()

    else:
        print("Invalid operation.")

if __name__ == "__main__":
    main()
