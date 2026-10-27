
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <ctype.h>
#include <time.h>

#define MAXLINE 4096
#define MAXARGS 128

static char previous[MAXLINE] = "";
static const char *eventfile;

static void event_log(pid_t pid, pid_t parent,
                      const char *state, const char *cmd) {
    if (!eventfile || !*eventfile) return;

    int fd = open(eventfile, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) return;

    char buf[8192];
    int n = snprintf(buf, sizeof(buf),
        "%ld\t%ld\t%ld\t%s\t%s\n",
        (long)time(NULL), (long)pid, (long)parent, state, cmd);

    if (n > 0 && n < (int)sizeof(buf))
        (void)write(fd, buf, (size_t)n);

    close(fd);
}

static void release(char **args, int count) {
    for (int i = 0; i < count; i++)
        free(args[i]);
}

static int tokenize(const char *p, char **args) {
    int n = 0;

    while (*p) {
        while (isspace((unsigned char)*p)) p++;
        if (!*p) break;

        if (n >= MAXARGS - 1) goto bad;

        char token[MAXLINE];
        size_t j = 0;
        char quote = 0;

        if (strchr("|<>&", *p)) {
            token[j++] = *p++;
        } else {
            while (*p) {
                if (!quote &&
                    (isspace((unsigned char)*p) ||
                     strchr("|<>&", *p)))
                    break;

                if (*p == '\'' || *p == '"') {
                    if (!quote) {
                        quote = *p++;
                        continue;
                    }
                    if (quote == *p) {
                        quote = 0;
                        p++;
                        continue;
                    }
                }

                if (*p == '\\' && p[1] && quote != '\'') {
                    p++;
                    if (quote == '"' &&
                        *p != '"' && *p != '\\' &&
                        *p != '$' && *p != '`') {
                        if (j >= MAXLINE - 1) goto bad;
                        token[j++] = '\\';
                    }
                }

                if (j >= MAXLINE - 1) goto bad;
                token[j++] = *p++;
            }
        }

        if (quote) {
            fprintf(stderr, "Unclosed quote\n");
            goto bad;
        }

        token[j] = '\0';
        args[n] = strdup(token);
        if (!args[n]) goto bad;
        n++;
    }

    args[n] = NULL;
    return n;

bad:
    fprintf(stderr, "Invalid command or too many arguments\n");
    release(args, n);
    return -1;
}

static void reap_background(void) {
    int status;
    pid_t pid;

    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        event_log(pid, getpid(),
            WIFEXITED(status) && WEXITSTATUS(status) == 0
                ? "completed" : "failed",
            "background");
    }
}

static int execute(const char *line) {
    char *args[MAXARGS] = {0};
    char *left[MAXARGS] = {0};
    char *right[MAXARGS] = {0};

    int total = tokenize(line, args);
    if (total < 0) return 2;
    if (total == 0) return 0;

    int n = total;
    int result = 0;
    int background = 0;
    int pipe_seen = 0;
    int l = 0, r = 0;

    char *infile = NULL;
    char *outfile = NULL;

    if (!strcmp(args[n - 1], "&")) {
        background = 1;
        n--;
    }

    if (n == 0) {
        fprintf(stderr, "Missing command\n");
        result = 2;
        goto cleanup;
    }

    for (int i = 0; i < n; i++) {
        if (!strcmp(args[i], "|")) {
            if (pipe_seen || !l) {
                fprintf(stderr, "Invalid pipe\n");
                result = 2;
                goto cleanup;
            }
            pipe_seen = 1;
            continue;
        }

        if (!strcmp(args[i], "<") ||
            !strcmp(args[i], ">")) {

            int input = !strcmp(args[i], "<");

            if (i + 1 >= n ||
                strchr("|<>&", args[i + 1][0])) {
                fprintf(stderr, "Missing redirection filename\n");
                result = 2;
                goto cleanup;
            }

            if ((input && infile) ||
                (!input && outfile)) {
                fprintf(stderr, "Duplicate redirection\n");
                result = 2;
                goto cleanup;
            }

            if (input)
                infile = args[++i];
            else
                outfile = args[++i];

            continue;
        }

        if (!strcmp(args[i], "&")) {
            fprintf(stderr, "& must be last\n");
            result = 2;
            goto cleanup;
        }

        if (!pipe_seen)
            left[l++] = args[i];
        else
            right[r++] = args[i];
    }

    left[l] = NULL;
    right[r] = NULL;

    if (!l || (pipe_seen && !r)) {
        fprintf(stderr, "Missing command\n");
        result = 2;
        goto cleanup;
    }

    int count = pipe_seen ? 2 : 1;
    int fds[2] = {-1, -1};
    pid_t pids[2] = {-1, -1};
    int started = 0;

    if (count == 2 && pipe(fds) != 0) {
        perror("pipe");
        result = 1;
        goto cleanup;
    }

    for (int k = 0; k < count; k++) {
        pid_t pid = fork();

        if (pid < 0) {
            perror("fork");
            result = 1;
            break;
        }

        if (pid == 0) {
            if (count == 2) {
                if (dup2(
                    k == 0 ? fds[1] : fds[0],
                    k == 0 ? STDOUT_FILENO : STDIN_FILENO
                ) < 0) _exit(1);

                close(fds[0]);
                close(fds[1]);
            }

            if (k == 0 && infile) {
                int fd = open(infile, O_RDONLY);

                if (fd < 0) {
                    perror(infile);
                    _exit(1);
                }

                if (dup2(fd, STDIN_FILENO) < 0)
                    _exit(1);

                close(fd);
            }

            if (k == count - 1 && outfile) {
                int fd = open(outfile,
                    O_WRONLY | O_CREAT | O_TRUNC, 0644);

                if (fd < 0) {
                    perror(outfile);
                    _exit(1);
                }

                if (dup2(fd, STDOUT_FILENO) < 0)
                    _exit(1);

                close(fd);
            }

            char **cmd = k == 0 ? left : right;
            execvp(cmd[0], cmd);
            perror(cmd[0]);
            _exit(127);
        }

        pids[started++] = pid;
        event_log(pid, getpid(), "running", line);
    }

    if (count == 2) {
        close(fds[0]);
        close(fds[1]);
    }

    if (started == count && background) {
        printf("[background] PID %ld\n", (long)pids[0]);
        fflush(stdout);
        goto cleanup;
    }

    for (int k = 0; k < started; k++) {
        int st = 0;

        if (waitpid(pids[k], &st, 0) >= 0) {
            int code = WIFEXITED(st)
                ? WEXITSTATUS(st)
                : WIFSIGNALED(st)
                    ? 128 + WTERMSIG(st) : 1;

            event_log(pids[k], getpid(),
                code == 0 ? "completed" : "failed",
                line);

            if (k == started - 1 && result == 0)
                result = code;
        }
    }

cleanup:
    release(args, total);
    return result;
}

int main(int argc, char **argv) {
    eventfile = getenv("OSH_EVENTS");

    int single = argc == 3 &&
                 !strcmp(argv[1], "-c");

    if (argc > 1 && !single) {
        fprintf(stderr,
            "Usage: %s [-c command]\n", argv[0]);
        return 2;
    }

    char *line = NULL;
    size_t capacity = 0;
    int result = 0;

    for (;;) {
        reap_background();

        if (single) {
            line = strdup(argv[2]);
            if (!line) return 1;
        } else {
            printf("osh> ");
            fflush(stdout);

            if (getline(&line, &capacity, stdin) < 0)
                break;
        }

        line[strcspn(line, "\r\n")] = '\0';

        if (!strcmp(line, "exit"))
            break;

        if (!strcmp(line, "!!")) {
            if (!previous[0]) {
                fprintf(stderr,
                    "No commands in history.\n");
                result = 2;

                if (single) break;
                continue;
            }

            char *copy = strdup(previous);

            if (!copy) {
                result = 1;
                break;
            }

            if (single) {
                free(line);
                line = copy;
            } else {
                size_t len = strlen(copy) + 1;

                if (capacity < len) {
                    char *resized = realloc(line, len);

                    if (!resized) {
                        free(copy);
                        result = 1;
                        break;
                    }

                    line = resized;
                    capacity = len;
                }

                memcpy(line, copy, len);
                free(copy);
            }

            printf("%s\n", line);
            fflush(stdout);
        } else if (*line) {
            snprintf(previous, sizeof(previous),
                     "%s", line);
        }

        if (*line)
            result = execute(line);

        if (single) break;
    }

    free(line);
    return result;
}
