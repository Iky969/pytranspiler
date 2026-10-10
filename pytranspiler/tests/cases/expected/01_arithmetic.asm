global add
add:
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
    jmp .L_end_add
.L_end_add:
    mov rsp, rbp
    pop rbp
    ret

global mix
mix:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov qword [rbp-16], rsi
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    push rax
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    sub rax, r11
    mov r11, rax
    pop rax
    imul rax, r11
    mov r11, rax
    pop rax
    add rax, r11
    jmp .L_end_mix
.L_end_mix:
    mov rsp, rbp
    pop rbp
    ret

global mul
mul:
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
    jmp .L_end_mul
.L_end_mul:
    mov rsp, rbp
    pop rbp
    ret

global sub
sub:
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
    jmp .L_end_sub
.L_end_sub:
    mov rsp, rbp
    pop rbp
    ret
