global combine
combine:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    mov qword [rbp-8], rdi
    mov qword [rbp-16], rsi
    mov qword [rbp-24], rdx
    mov qword [rbp-32], rcx
    mov qword [rbp-40], r8
    mov qword [rbp-48], r9
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    add rax, r11
    push rax
    mov rax, qword [rbp-24]
    push rax
    mov rax, qword [rbp-32]
    mov r11, rax
    pop rax
    sub rax, r11
    mov r11, rax
    pop rax
    imul rax, r11
    push rax
    mov rax, qword [rbp-40]
    push rax
    mov rax, qword [rbp-48]
    mov r11, rax
    pop rax
    imul rax, r11
    mov r11, rax
    pop rax
    add rax, r11
    jmp .L_end_combine
.L_end_combine:
    mov rsp, rbp
    pop rbp
    ret

global deep
deep:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    mov qword [rbp-8], rdi
    mov qword [rbp-16], rsi
    mov qword [rbp-24], rdx
    mov qword [rbp-32], rcx
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    add rax, r11
    push rax
    mov rax, qword [rbp-24]
    push rax
    mov rax, qword [rbp-32]
    mov r11, rax
    pop rax
    add rax, r11
    mov r11, rax
    pop rax
    imul rax, r11
    push rax
    mov rax, qword [rbp-8]
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    sub rax, r11
    push rax
    mov rax, qword [rbp-24]
    push rax
    mov rax, qword [rbp-32]
    mov r11, rax
    pop rax
    sub rax, r11
    mov r11, rax
    pop rax
    imul rax, r11
    mov r11, rax
    pop rax
    sub rax, r11
    jmp .L_end_deep
.L_end_deep:
    mov rsp, rbp
    pop rbp
    ret
