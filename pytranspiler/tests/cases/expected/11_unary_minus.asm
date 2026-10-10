global neg_literal
neg_literal:
    push rbp
    mov rbp, rsp
    mov rax, 0
    push rax
    mov rax, 42
    mov r11, rax
    pop rax
    sub rax, r11
    jmp .L_end_neg_literal
.L_end_neg_literal:
    mov rsp, rbp
    pop rbp
    ret

global neg_var
neg_var:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov rax, 0
    push rax
    mov rax, qword [rbp-8]
    mov r11, rax
    pop rax
    sub rax, r11
    jmp .L_end_neg_var
.L_end_neg_var:
    mov rsp, rbp
    pop rbp
    ret

global sign_flip
sign_flip:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    mov qword [rbp-8], rdi
    mov rax, qword [rbp-8]
    mov qword [rbp-16], rax
    mov rax, 0
    push rax
    mov rax, qword [rbp-16]
    mov r11, rax
    pop rax
    sub rax, r11
    mov qword [rbp-16], rax
    mov rax, qword [rbp-16]
    jmp .L_end_sign_flip
.L_end_sign_flip:
    mov rsp, rbp
    pop rbp
    ret
