global total
total:
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
    add rax, r11
    mov qword [rbp-24], rax
    mov rax, qword [rbp-24]
    push rax
    mov rax, 10
    mov r11, rax
    pop rax
    add rax, r11
    mov qword [rbp-24], rax
    mov rax, qword [rbp-24]
    jmp .L_end_total
.L_end_total:
    mov rsp, rbp
    pop rbp
    ret

global twice
twice:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov rax, qword [rbp-8]
    push rax
    mov rax, 2
    mov r11, rax
    pop rax
    imul rax, r11
    mov qword [rbp-16], rax
    mov rax, qword [rbp-16]
    jmp .L_end_twice
.L_end_twice:
    mov rsp, rbp
    pop rbp
    ret
