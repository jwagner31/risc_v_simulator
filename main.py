import argparse
from pipeline_simulator import PipelineSimulator
from disassembler import Disassembler

def main():
    # Command line args
    parser = argparse.ArgumentParser(description="RISC-V Simulator")
    parser.add_argument("input_file_name", help="Input")
    parser.add_argument("output_file_name", help="output file for disassembler")
    parser.add_argument("output_file_name_2", help="output file for simulator")
    parser.add_argument('oper', choices=['dis', 'sim'], help="Operation to perform")
    parser.add_argument('-T', metavar="m:n", type=str, help="Trace mode - start (m) and end (n) cycles")

    args = parser.parse_args()

    if args.oper == 'dis':
        disassembler = Disassembler(args.input_file_name, args.output_file_name)
        disassembler.disassemble()

    elif args.oper == 'sim':
        if args.T:
            trace_start, trace_end = map(int, args.T.split(":"))
        else:
            trace_start, trace_end = None, None

        with open(args.output_file_name, 'r') as file:
            instructions = file.readlines()

        instructions = [instr.strip() for instr in instructions if instr.strip() != '']

        pipeline_sim = PipelineSimulator(instructions, trace_start, trace_end, args.output_file_name_2)
        pipeline_sim.simulate()

    else:
        print("Invalid operation.")

if __name__ == "__main__":
    main()
