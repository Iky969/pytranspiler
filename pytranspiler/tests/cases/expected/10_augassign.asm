global add_assign
add_assign:
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
    add rax, r11
    mov qword [rbp-8], rax
    mov rax, qword [rbp-8]
    jmp .L_end_add_assign
.L_end_add_assign:
    mov rsp, rbp
    pop rbp
    ret

global chain_assign
chain_assign:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov qword [rbp-8], rdi
    mov qword [rbp-16], rsi
    mov qword [rbp-24], rdx
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    add rax, r11
    mov qword [rbp-8], rax
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-24]
    mov r11, rax
    pop rax
    imul rax, r11
    mov qword [rbp-8], rax
    mov rax, qword [rbp-8]
    jmp .L_end_chain_assign
.L_end_chain_assign:
    mov rsp, rbp
    pop rbp
    ret

global mul_assign
mul_assign:
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
    imul rax, r11
    mov qword [rbp-8], rax
    mov rax, qword [rbp-8]
    jmp .L_end_mul_assign
.L_end_mul_assign:
    mov rsp, rbp
    pop rbp
    ret

global sub_assign
sub_assign:
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
    sub rax, r11
    mov qword [rbp-8], rax
    mov rax, qword [rbp-8]
    jmp .L_end_sub_assign
.L_end_sub_assign:
    mov rsp, rbp
    pop rbp
    ret
