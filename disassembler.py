# disassembler.py

import argparse

class Disassembler:

    def __init__(self, input_file_name, output_file_name):
        # Class takes in files as inputs
        self.input_file_name = input_file_name
        self.output_file_name = output_file_name 
        self.address = 496 # Starting address of instructions
        self.result = [] # Stores the disassembled instructions
        self.ret = False # Flag to indicate when I hit RET

    # num --> immediate value extracted
    # bits --> number of bits 
    def get_signed(self, num, bits):
        MSB = 1 << (bits - 1)
        # num is a binary before, becomes signed integer
        if num & (MSB): # if number negetive, sign extend with 1s
            num -= 1 << bits
        return num
    
    def decode_instruction(self, instruction):

        # Extract the standard risc fields, broken down later if needed for imm
        opcode = instruction & 0b1111111  # 7 bits opcode. 0-6
        rd = (instruction >> 7) & 0b11111  # 5 bits rd. 11-7
        funct3 = (instruction >> 12) & 0b111  # 3 bits funct3. 14-12
        rs1 = (instruction >> 15) & 0b11111  # 5 bits for rs1. 19-15
        rs2 = (instruction >> 20) & 0b11111  # 5 bits for rs2. 24-20
        funct7 = (instruction >> 25) & 0b1111111  # 7 bit funct7. 31-25

        # First 32 bits of output for an instruction should be split 7, 5, 5, 3, 5, and 7
        binary_split = f"{funct7:07b} {rs2:05b} {funct3:03b} {rs1:05b} {rd:05b} {opcode:07b}"

        # R type op
        if opcode == 0b0110011:
            if funct3 == 0b000 and funct7 == 0b0000000:  # ADD
                # add rd, rs1, rs2
                return f"{binary_split}\t{self.address}\tADD   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b000 and funct7 == 0b0100000:  # SUB
                # sub rd, rs1, rs2
                return f"{binary_split}\t{self.address}\tSUB   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b010 and funct7 == 0b0000000:  # SLT 
                # rd = rs1 < rs2
                return f"{binary_split}\t{self.address}\tSLT   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b111 and funct7 == 0b0000000:  #  AND
                return f"{binary_split}\t{self.address}\tAND   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b110 and funct7 == 0b0000000:  # OR
                return f"{binary_split}\t{self.address}\tOR    x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b100 and funct7 == 0b0000000:  #XOR
                return f"{binary_split}\t{self.address}\tXOR   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b001 and funct7 == 0b0000000:  #SLL 
                return f"{binary_split}\t{self.address}\tSLL   x{rd}, x{rs1}, x{rs2}"
            elif funct3 == 0b101 and funct7 == 0b0000000:  # SRL 
                return f"{binary_split}\t{self.address}\tSRL   x{rd}, x{rs1}, x{rs2}"
        # Load (only LW)
        elif opcode == 0b0000011:
            # Load is the only L type, so no further checks needed
            # Extract unsigned immediate in [31-20]
            imm = (instruction >> 20) & 0b111111111111
            signed_imm = self.get_signed(imm, 12) # extend to XLEN = 12
            return f"{binary_split}\t{self.address}\tLW    x{rd}, {signed_imm}(x{rs1})"
        
        # Store (only SW)
        elif opcode == 0b0100011:
            # Store is only S type
            # [31-25] and [11-7] are the immediate 
            imm = ((instruction >> 25) << 5) | (instruction >> 7) & 0b11111
            signed_imm = self.get_signed(imm, 12)
            return f"{binary_split}\t{self.address}\tSW    x{rs2}, {signed_imm}(x{rs1})"
        
        # I 
        elif opcode == 0b0010011:
            # imm same for ADDI and SLTI, [31-20]
            imm = (instruction >> 20) & 0b111111111111
            signed_imm = self.get_signed(imm, 12)
            # ADDI
            if funct3 == 0b000:
                return f"{binary_split}\t{self.address}\tADDI  x{rd}, x{rs1}, {signed_imm}"
            # SLTI
            elif funct3 == 0b010:
                return f"{binary_split}\t{self.address}\tSLTI  x{rd}, x{rs1}, {signed_imm}"
            
        ### Branch, J, JALR left
            
        # Branch
        elif opcode == 0b1100011:
            # Extracting immediate
            # so branch immediate have two MSB in 31 and 7
            # order --> [31] [7] [30-25] [11-8]
            imm = ((instruction >> 31) & 0b1) << 12 | ((instruction >> 25) & 0b111111) << 5 |((instruction >> 8) & 0b1111) << 1 | ((instruction >> 7) & 0b1) << 11
            signed_imm = self.get_signed(imm, 13)
               # BNE
            if funct3 == 0b001:
                return f"{binary_split}\t{self.address}\tBNE   x{rs1}, x{rs2}, {signed_imm}"
            # BLT
            elif funct3 == 0b100:
                return f"{binary_split}\t{self.address}\tBLT   x{rs1}, x{rs2}, {signed_imm}"
            # BGE
            elif funct3 == 0b101:
                return f"{binary_split}\t{self.address}\tBGE   x{rs1}, x{rs2}, {signed_imm}"
            #BEQ
            elif funct3 == 0b000:
                return f"{binary_split}\t{self.address}\tBEQ   x{rs1}, x{rs2}, {signed_imm}"
            
        # JAL
        elif opcode == 0b1101111:
            # Extracting immediate
            # order = [31] [19-12] [20] [30-21] (bit position)
            imm = ((instruction >> 31) & 0b1) << 20 | ((instruction >> 12) & 0b11111111) << 12 | ((instruction >> 20) & 0b1) << 11 | ((instruction >> 21) & 0b1111111111) << 1
            signed_imm = self.get_signed(imm, 21)    # imm is length 21 on this
            write_to = self.address + signed_imm
            return f"{binary_split}\t{self.address}\tJ\t#{write_to}  //JAL x{rd}, {signed_imm}"

        
        # JALR
        elif opcode == 0b1100111:
            # order = [31-20] size = 12
            imm = (instruction >> 20) & 0b111111111111
            signed_imm = self.get_signed(imm, 12)
            self.ret = True # Hit ret so change bool
            return f"{binary_split}\t{self.address}\tRET   //JALR x0, x1, 0"

        return f"{instruction}\t\t{self.address}\t0"
    
    def decode_data(self, line):
        data = int(line, 2)
        return f"{line}\t\t{self.address}\t{data}"

    # primary logic. breaks down file line by line. Decodes each line and then writes it to result
    def disassemble(self):

        # Get lines from input file
        f = open(self.input_file_name, 'r')
        lines = []
        for line in f.readlines():
            lines.append(line.strip())
        f.close()

        #lines now contains all the lines from the input file
        # iterate through each line and decode it
        for line in lines:
            if len(line) == 0:
                continue
            elif len(line) != 32:
                print("Wrong line length")
                break
            if not self.ret:
                #print(line)
                instruction = self.decode_instruction(int(line,2))
            else:
                #print(line)
                instruction = self.decode_data(line)
            self.result.append(instruction)
            self.address += 4

        # Just open output file and write the lines stored in result list
        f_out = open(self.output_file_name, 'w')
        for line in self.result:
            f_out.write(line +'\n')
        f_out.close()