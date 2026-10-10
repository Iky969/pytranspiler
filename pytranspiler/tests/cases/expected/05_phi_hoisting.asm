global branch_then_loop
branch_then_loop:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov rax, qword [rbp-8]
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    cmp rax, r11
    setg al
    movzx rax, al
    cmp rax, 0
    je .L_else_branch_then_loop_if_1
    mov rax, qword [rbp-8]
    mov qword [rbp-16], rax
    jmp .L_end_branch_then_loop_if_1
.L_else_branch_then_loop_if_1:
    mov rax, 0
    mov qword [rbp-16], rax
.L_end_branch_then_loop_if_1:
.L_start_branch_then_loop_while_2:
    mov rax, qword [rbp-16]
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    cmp rax, r11
    setg al
    movzx rax, al
    cmp rax, 0
    je .L_end_branch_then_loop_while_2
    mov rax, qword [rbp-16]
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    sub rax, r11
    mov qword [rbp-16], rax
    jmp .L_start_branch_then_loop_while_2
.L_end_branch_then_loop_while_2:
    mov rax, qword [rbp-16]
    jmp .L_end_branch_then_loop
.L_end_branch_then_loop:
    mov rsp, rbp
    pop rbp
    ret

global choose
choose:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov rax, qword [rbp-8]
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    cmp rax, r11
    setg al
    movzx rax, al
    cmp rax, 0
    je .L_else_choose_if_1
    mov rax, 10
    mov qword [rbp-16], rax
    jmp .L_end_choose_if_1
.L_else_choose_if_1:
    mov rax, 20
    mov qword [rbp-16], rax
.L_end_choose_if_1:
    mov rax, qword [rbp-16]
    jmp .L_end_choose
.L_end_choose:
    mov rsp, rbp
    pop rbp
    ret

global clamp
clamp:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov qword [rbp-8], rdi
    mov qword [rbp-16], rsi
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    cmp rax, r11
    setg al
    movzx rax, al
    cmp rax, 0
    je .L_else_clamp_if_1
    mov rax, qword [rbp-16]
    mov qword [rbp-24], rax
    jmp .L_end_clamp_if_1
.L_else_clamp_if_1:
    mov rax, qword [rbp-8]
    mov qword [rbp-24], rax
.L_end_clamp_if_1:
    mov rax, qword [rbp-24]
    jmp .L_end_clamp
.L_end_clamp:
    mov rsp, rbp
    pop rbp
    ret
