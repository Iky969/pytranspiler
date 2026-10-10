global max_of
max_of:
    push rbp
    mov rbp, rsp
    sub rsp, 16
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
    je .L_else_max_of_if_1
    mov rax, qword [rbp-8]
    jmp .L_end_max_of
.L_else_max_of_if_1:
    mov rax, qword [rbp-16]
    jmp .L_end_max_of
.L_end_max_of_if_1:
.L_end_max_of:
    mov rsp, rbp
    pop rbp
    ret

global sign
sign:
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
    je .L_else_sign_if_1
    mov rax, 1
    jmp .L_end_sign
.L_else_sign_if_1:
    mov rax, qword [rbp-8]
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    cmp rax, r11
    setl al
    movzx rax, al
    cmp rax, 0
    je .L_else_sign_if_2
    mov rax, 1
    neg rax
    jmp .L_end_sign
.L_else_sign_if_2:
    mov rax, 0
    jmp .L_end_sign
.L_end_sign_if_2:
.L_end_sign_if_1:
.L_end_sign:
    mov rsp, rbp
    pop rbp
    ret

global sum_to
sum_to:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov qword [rbp-8], rdi
    mov rax, 0
    mov qword [rbp-16], rax
    mov rax, qword [rbp-8]
    mov qword [rbp-24], rax
.L_start_sum_to_while_1:
    mov rax, qword [rbp-24]
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    cmp rax, r11
    setg al
    movzx rax, al
    cmp rax, 0
    je .L_end_sum_to_while_1
    mov rax, qword [rbp-16]
    push rax
    mov rax, qword [rbp-24]
    mov r11, rax
    pop rax
    add rax, r11
    mov qword [rbp-16], rax
    mov rax, qword [rbp-24]
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    sub rax, r11
    mov qword [rbp-24], rax
    jmp .L_start_sum_to_while_1
.L_end_sum_to_while_1:
    mov rax, qword [rbp-16]
    jmp .L_end_sum_to
.L_end_sum_to:
    mov rsp, rbp
    pop rbp
    ret
