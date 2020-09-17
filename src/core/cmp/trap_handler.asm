 


    .text

header_size = 12 #in bytes
header_size_slot = 0
header_next_slot = 4
header_reachable_slot = 8
alloc_size       = 2048
total_alloc_size = alloc_size + header_size
neg_header_size = 0-header_size
free_list = 0
used_list = header_size
state_size = 4
stack_base = -4
init_alloc_size = (header_size*2) +  state_size
object_mark = -1
meta_data_object_size = 4   #in words


    .globl main
main:
    jal mem_manager_init

    li $v0 10
    syscall
    

#####################################################################################################
# Initialize memory manager                                                                         #
# Args:                                                                                             #
#                                                                                                   #
# Return:                                                                                           # 
#                                                                                                   #
# Summary:                                                                                          #
#    The initial blocks for Free-List and Used-List are created.                                    #
#    The $gp is set to use as reference when initial blocks or values related to memory manager     #
#    state are needed.                                                                              #
#    A block of size alloc_size is created an added to Free-List                                    #
##################################################################################################### 
mem_manager_init:
    addiu $sp $sp -16
    sw $v0 0($sp)
    sw $a0 4($sp)
    sw $a1 8($sp)
    sw $ra 12($sp)


    li $v0 9
    li $a0 init_alloc_size
    syscall                         #Creating free-list start point
    move $gp $v0                    
    addiu $gp $gp state_size

    sw $zero header_size_slot($gp)       #The free-list start with a block without space, just header, that will always be there.
    sw $zero header_next_slot($gp)
    sw $zero header_reachable_slot($gp) 

    move $a0 $gp
    li $a1 alloc_size
    jal extend_heap

    addiu $a0 $a0 header_size
    sw $zero header_size_slot($a0)      #The used-list start with a block without space, just header, that will always be there.
    sw $zero header_next_slot($a0)
    sw $zero header_reachable_slot($a0)

    sw $sp stack_base($gp)
    
    lw $v0 0($sp)
    lw $a0 4($sp)
    lw $a1 8($sp)
    lw $ra 12($sp)
    addiu $sp $sp 16

    jr $ra
    

#####################################################################################################
# Free a block previously allocated                                                                 #
# Args:                                                                                             #
# $a0 Block to free address                                                                         #
# Return:                                                                                           # 
#                                                                                                   #
# Summary:                                                                                          #
#    Remove the block from the used-list and add it to the free-list                                #
##################################################################################################### 
free_block:
    addiu $sp $sp -28
    sw $t0 0($sp)
    sw $t1 4($sp)
    sw $t2 8($sp)
    sw $a0 12($sp)
    sw $ra 16($sp)
    sw $t3 20($sp)
    sw $t4 24($sp)

    move $t0 $a0
    
    addiu $t1 $gp free_list         # Store in $t1 the initial block of the free-list

    addiu $t3 $gp used_list         # Store in $t3 the initial block of the used-list

free_block_loop_used_list:          # Iterate througth the used-list until find the block
    lw $t4 header_next_slot($t3)
    beq $t4 $t0 free_block_loop_free_list
    move $t3 $t4
    j free_block_loop_used_list


free_block_loop_free_list:          # Iterate througth the free-list to find the antecesor of the block in the free-list
    lw $t2 header_next_slot($t1)
    beq $t2 $zero free_block_founded_prev
    bge $t2 $t0 free_block_founded_prev
    move $t1 $t2
    j free_block_loop_free_list

free_block_founded_prev:        
    # Remove the block from the used-list
    lw $t4 header_next_slot($t0)
    sw $t4 header_next_slot($t3)
    
    # Add the block to the free-list
    sw $t2 header_next_slot($t0)
    sw $t0 header_next_slot($t1)

free_block_end:
   
    # Try to merge the list where the new block was added
    move $a0 $t0
    jal expand_block
    move $a0 $t1
    jal expand_block

    lw $t0 0($sp)
    lw $t1 4($sp)
    lw $t2 8($sp)
    lw $a0 12($sp)
    lw $ra 16($sp)
    lw $t3 20($sp)
    lw $t4 24($sp)
    addiu $sp $sp 28

    jr $ra


#####################################################################################################
# Merge two continuos blocks of the free-list                                                       #
# Args:                                                                                             #
# $a0  First of the two blocks to merge                                                             #
# Return:                                                                                           # 
#                                                                                                   #
# Summary:                                                                                          #
#    Check if a block can be merged with its sucesor in the free list                               #
##################################################################################################### 
expand_block:
    addiu $sp $sp -16
    sw $t0 0($sp)
    sw $t1 4($sp)
    sw $t2 8($sp)
    sw $t3 12($sp)

    
    addiu $t0 $gp free_list     # $t0 = the initial block of the free-list

    beq $t0 $a0 expand_block_end  # The initial block can't be expanded, the initial block always will have size 0

    move $t0 $a0

    # Check if the block and its sucesor in the free list are contiguous in memory
    lw $t1 header_next_slot($t0)
    lw $t2 header_size_slot($t0)
    move $t3 $t2
    addiu $t2 $t2 header_size
    addu $t2 $t2 $t0
    beq $t2 $t1 expand_block_expand
    j expand_block_end

expand_block_expand:    #Increment the size of the first block and update next field
    lw $t2 header_size_slot($t1)
    addi $t2 $t2 header_size
    add $t2 $t2 $t3
    sw $t2 header_size_slot($t0)
    lw $t1 header_next_slot($t1)
    sw $t1 header_next_slot($t0)
    
expand_block_end:
    lw $t0 0($sp)
    lw $t1 4($sp)
    lw $t2 8($sp)
    lw $t3 12($sp)
    addiu $sp $sp 16

    jr $ra


#####################################################################################################
# Allocate more memory for the process and add it to the free-list                                  #
# Args:                                                                                             #
# $a0  Last block of the free-list                                                                  #
# $a1  Memory amount to alloc                                                                       #
# Return:                                                                                           # 
#                                                                                                   #
# Summary:                                                                                          #
#    More memory is allocated and add it to the free-list as a block.                               #
##################################################################################################### 
extend_heap:
    addiu $sp $sp -12
    sw $a0 0($sp)
    sw $a1 4($sp)
    sw $t0 8($sp)

    # Increase the amount of memory by header_size to create a block with that size
    li $v0 9
    addiu $a0 $a1 header_size
    syscall
    
    # Set values of the block_header
    move $t0 $a1 
    sw $t0 header_size_slot($v0)
    sw $zero header_next_slot($v0)
    sw $zero header_reachable_slot($v0)

    # Add block to the end of the free-list
    lw $t0, 0($sp)
    sw $v0 header_next_slot($t0)

    move $a0 $t0
    lw $a1 4($sp)
    lw $t0 8($sp)
    addiu $sp $sp 12

    jr $ra


  
#####################################################################################################
# Split a block into two blocks, one of the requested size and the other with the rest.             #
# Args:                                                                                             #
# $a0  Address of the block to split                                                                #
# $a1  Size requested for one block                                                                 #
# Return:                                                                                           # 
#                                                                                                   #
# Summary:                                                                                          #
#    The block is splitted into two blocks if the size allow it.                                    #
##################################################################################################### 
split_block:
    addiu $sp $sp -16
    sw $t0 0($sp)
    sw $t1 4($sp)
    sw $a0 8($sp)
    sw $a1 12($sp)

    # Check if the block can be splitted in two blocks, one of the requested size
    lw $t0 header_size_slot($a0)
    bgt $a1 $t0 split_block_error_small
    
    # Check if after a split the block there is enough space to create another block, if there is not do not split
    sub $t0 $t0 $a1
    li $t1 header_size
    ble $t0 $t1 split_block_same_size

    # Compute the address of the second block
    addu $t0 $a0 $a1
    addiu $t0 $t0 header_size     

    #Update headers of the two blocks
    lw $t1 header_next_slot($a0)    
    sw $t1 header_next_slot($t0)
    sw $t0 header_next_slot($a0)

    lw $t1 header_size_slot($a0)    #update sizes
    sub $t1 $t1 $a1

    addi $t1 $t1 neg_header_size
    sw $t1 header_size_slot($t0)
    sw $a1 header_size_slot($a0)
    move $v0 $a0
    j split_block_end

split_block_same_size:
    move $v0 $a0
    j split_block_end

split_block_error_small:
    j split_block_end

split_block_end:
    lw $t0 0($sp)
    lw $t1 4($sp)
    lw $a0 8($sp)
    lw $a1 12($sp)
    addiu $sp $sp 16

    jr $ra


#####################################################################################################
# Best Fit strategy is used to select the block                                                     #
# Args:                                                                                             #
# $a0 size to alloc                                                                                 #
# Return:                                                                                           # 
# $v0 address of allocated block                                                                    #
# Summary:                                                                                          #
#   Actual block is store in $t0, the size block is checked to know if it is a                      #
#   valid block (a block is valid if its size is larger or equal than the required size),           #
#   if the block is valid we compare it with the actual best block and keep the shorter block.      #
#   If there is not a block with the required size, a new block of size                             #
#   max(total_alloc_size, size requested) is requested with sbrk and splitted if necessary          #
##################################################################################################### 
malloc:
    move $v0 $zero
    addiu $sp $sp -28
    sw $t1 0($sp)
    sw $t0 4($sp)
    sw $a0 8($sp)
    sw $a1 12($sp)
    sw $ra 16($sp)
    sw $t2 20($sp)
    sw $t3 24($sp)
    
    addiu $t0 $gp free_list
    j malloc_loop

malloc_end:

    move $a0 $v0
    lw $a1 8($sp)                  # a1 = requested block size
    jal split_block

    lw $t1 header_next_slot($v0)
    sw $t1 header_next_slot($t3)

    addiu $t1 $gp used_list
    lw $a0 header_next_slot($t1)

    sw $a0 header_next_slot($v0)
    sw $v0 header_next_slot($t1)
    
    addiu $v0 $v0 header_size

    lw $t3 24($sp)
    lw $t2 20($sp)
    lw $ra 16($sp)
    lw $a1 12($sp)
    lw $a0 8($sp)
    lw $t0 4($sp)
    lw $t1 0($sp)
    addiu $sp $sp 28

    jr $ra
#######################################################################
# t0 = actual block address                                           #
#######################################################################
malloc_loop:
    move $t2 $t0                        # save previous block in $t2 (this is usefull when we lw $t3 24($sp)need to alloc the new block)
    lw $t0 header_next_slot($t0)        # t0 = next block address
    beq $t0 $zero malloc_search_end     # if t0 == 0 we reach to the free-list end
    j malloc_check_valid_block

#######################################################################
# $v0 = actual selected block address                                 #
#######################################################################
malloc_search_end:
    beq $v0 $zero malloc_alloc_new_block  # if v0 == 0 a valid block was not found
    j malloc_end

#######################################################################
# t2 = last block of free list                                        #
# a0 = requested block size                                           #
#######################################################################
malloc_alloc_new_block:
    li $t1 alloc_size               # t1 = standard alloc size
    move $t3 $t2
    move $a1 $a0                    # a1 = requested block size
    move $a0 $t2                    # a0 = last block of free list
    bge $a1 $t1 malloc_big_block    # if the requested size is bigger than the standar alloc size go to malloc_big_block
    li $a1 alloc_size         # a1 = standard alloc size
    jal extend_heap
    
    j malloc_end

######################################################################
# a1 = requested block size                                          #
######################################################################
malloc_big_block:
    #addiu $a1 $a1 header_size              # Add header size to alloc size
    jal extend_heap
    j malloc_end



########################################################################
# t0 = actual block address                                            #                                            
########################################################################
malloc_check_valid_block:
    lw $t1 header_size_slot($t0)             # t1 = size new block
    bge $t1 $a0 malloc_valid_block    # the actual block have the required size
    j malloc_loop

########################################################################
# t0 = actual block address                                            #
# t1 = size actual block                                               #
# v0 = actual selected block address(0 if no one have been selected)   #
# v1 = actual selected block size                                      #
########################################################################
malloc_valid_block:
    beq $v0 $zero malloc_first_valid_block     # this is the first valid block
    bge $t1 $v1 malloc_loop                    # the selected block is smaller than actual block
    move $v0 $t0                        # selected block address = actual block address
    move $v1 $t1                        # selected block size = actual block size
    move $t3 $t2
    j malloc_loop


########################################################################
# t0 = actual block address                                            # 
# t1 = size actual block                                               # 
# v0 = actual selected block address(0 if no one have been selected)   #
# v1 = actual selected block size                                      #
########################################################################
malloc_first_valid_block:
    move $v0 $t0                        # selected block address = actual block address
    move $v1 $t1                        # selected block size    = actual block size
    move $t3 $t2 
    j malloc_loop



gc_collect:
    addiu $sp $sp -16
    sw $t0 0($sp)
    sw $t1 4($sp)
    sw $t2 8($sp)
    sw $t3 12($sp)

    li $t3 -1
    addiu $t0 $sp 16
    lw $t1 stack_base($gp)

gc_collect_loop:
    addiu $t0 $t0 4
    beq $t0 $t1 gc_collect_dfs
    j gc_collect_check_if_is_object

gc_collect_check_if_is_object:
    lw $t2 0($t0)
    blt $t2 $zero j gc_collect_loop
    bge $t2 type_number($zero) j gc_collect_loop
    lw $t2 4($t0)
    addiu $t2 $t2 -1
    ssl $t2 $t2 2
    addu $t2 $t0 $t2
    lw $t2 0($t2)
    bne $t2 object_mark($zero) gc_collect_loop

    sw $t3 header_reachable_slot($t2)
    
    j gc_collect_loop

gc_collect_dfs:
    addiu $t1 $gp used_list

gc_collect_outer_loop:
    lw $t1 header_next_slot($t1)
    lw $t2 header_reachable_slot($t1)
    beq $t2 $t3 gc_collect_expand

gc_collect_expand:
    lw $t4 4($t1)
    addi $t4 $t4 -3
    addiu $t5 $t1 8

gc_collect_end:
    lw $t0 0($sp)
    lw $t1 4($sp)
    lw $t2 8($sp)
    lw $t3 12($sp)

    addiu $sp $sp 16

    jr $ra


gc_collect_recursive_expand:
    addiu $sp $sp -12
    sw $a0 0($sp)
    sw $t0 4($sp)
    sw $t1 8($sp)

    move $t0 $a0


    lw $t1 4($a0)
    addi $t1 $t1 -3

gc_collect


  




$a0 address from 
$a1 address to
$a2 size
copy:
    addiu $sp $sp -16
    sw $a0 0($sp)
    sw $a1 4($sp)
    sw $a2 8($sp)
    sw $t0 12($sp)

copy_loop:
    beq $a2 $zero copy_end
    lw $t0 0($a0)
    sw $t0 0($a1)
    addiu $a0 $a0 4
    addiu $a1 $a1 4
    addi $a2 $a2 -4
    j copy_loop 

copy_end:
    lw $a0 0($sp)
    lw $a1 4($sp)
    lw $a2 8($sp)
    lw $t0 12($sp)
    addiu $sp $sp 16

    jr $ra



# $a0 address to check
check_if_is_object:
    addiu $sp $sp -20
    sw $t0 0($sp)
    sw $t1 4($sp)
    sw $t2 8($sp)
    sw $t3 12($sp)
    sw $a0 16($sp)

    move $t0 $a0

    li $v0 9
    move $a0 $zero
    syscall

    addiu $t1 $v0 -4    #Last word of heap

    blt $t0 $gp check_if_is_object_not_object
    bgt $t0 $t1 check_if_is_object_not_object
    lw $t2 0($t0)
    blt $t2 $zero check_if_is_object_not_object
    bgt $t2 type_number check_if_is_object_not_object

    addiu $t0 $t0 4
    blt $t0 $gp check_if_is_object_not_object
    bgt $t0 $t1 check_if_is_object_not_object
    lw $t2 0($t0)   #Store size in $t2

    addiu $t0 $t0 8
    
    li $t3 meta_data_object_size
    sub $t2 $t2 $t3 
    sll $t2 $t2 2

    addu $t0 $t0 $t2
    blt $t0 $gp check_if_is_object_not_object
    bgt $t0 $t1 check_if_is_object_not_object
    lw $t2 0($t0)
    bnq $t2 object_mark check_if_is_object_not_object
    li $v0 1
    j check_if_is_object_end
    
    
check_if_is_object_not_object:
    li $v0 0


check_if_is_object_end:
    lw $t0 0($sp)
    lw $t1 4($sp)
    lw $t2 8($sp)
    lw $t3 12($sp)
    lw $a0 16($sp)
    addiu $sp $sp 20

    jr $ra















