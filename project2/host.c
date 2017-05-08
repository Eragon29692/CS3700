#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/ether.h>
#include <stdlib.h>
#include <argp.h>               /* horribly non-standard */

static struct argp_option options[] = {
    {"silent", 's', 0, 0, "receive only, no transmit"},
    {0, 0}
};

struct ether_addr l_ether, r_ether;
int wirenum;
int silent;

static error_t parse_opt(int key, char *arg, struct argp_state *state)
{
    static int argnum = 0;
    
    switch (key) {
    case 's':
        silent = 1;
        break;
    case ARGP_KEY_ARG:
        if (argnum++ == 0)
            ether_aton_r(arg, &l_ether);
        else if (argnum++ == 1)
            wirenum = atoi(arg);
        else if (argnum++ == 2)
            ether_aton_r(arg, &r_ether);
        else
            argp_usage(state);
        break;
    case ARGP_KEY_END:
        if (argnum != 3)
            argp_usage(state);
        break;
    default:
        argp_usage(state);
        break;
    }
    return 0;
}
static char arg_doc[] = "LL:LL:LL:LL:LL:LL <wirenum> RR:RR:RR:RR:RR:RR";
static char doc_doc[] = "Host - send packets across the 'network'";

static struct argp argp = {options, parse_opt, arg_doc, doc_doc};

void *receive(void *arg)
{
    int i, len, sock = (int)arg;
    unsigned char buf[1500];    /* unsigned so printf %02x works... */
    
    while ((len = recv(sock, buf, sizeof(buf), 0)) > 0) {
        char tmp1[32], tmp2[32];
        struct ether_addr *dst = (struct ether_addr*)buf; /* very crude unpacking */
        struct ether_addr *src = (struct ether_addr*)&buf[6];
        printf("received dgram from %s to %s:", ether_ntoa_r(src, tmp1), ether_ntoa_r(dst, tmp2));
        for (i = 0; i < len; i++)
            printf("%02x ", buf[i]);
        printf("\n");
    }
    printf("lost connection\n");
    exit(0);
}

/* all bytes in AF_UNIX abstact socket names are significant, even 0s,
 * so we need this to be compatible with the python code in 'wires'
 */
int addrlen(struct sockaddr_un *a)
{
    return sizeof(a->sun_family) + 1 + strlen(&a->sun_path[1]);
}
        
int main(int argc, char **argv)
{

    argp_parse(&argp, argc, argv, ARGP_IN_ORDER, 0, 0);

    int s = socket(AF_UNIX, SOCK_SEQPACKET, 0);

    struct sockaddr_un l_unix = {.sun_family = AF_UNIX, .sun_path = {0,}};
    sprintf(&l_unix.sun_path[1], "%s.host-%s (wire %d)", getenv("USER"), argv[1], wirenum);
    bind(s, (struct sockaddr*)&l_unix, addrlen(&l_unix));

    struct sockaddr_un w_unix = {.sun_family = AF_UNIX, .sun_path = {0,}};
    sprintf(&w_unix.sun_path[1], "%s.wire.%d", getenv("USER"), wirenum);
    if (connect(s, (struct sockaddr*)&w_unix, addrlen(&w_unix)) < 0)
        perror("can't connect");

    pthread_t t;
    pthread_create(&t, NULL, receive, (void*)s);

    char packet[60] = {0,};
    memcpy(&packet[0], &r_ether, sizeof(r_ether));
    memcpy(&packet[6], &l_ether, sizeof(l_ether));
    short etype = htons(0x900);
    memcpy(&packet[12], &etype, sizeof(etype));
    strcpy(&packet[14], "\xDE\xAD\xBE\xEF\xDE\xAD\xBE\xEF");

    for (;;) {
        sleep(3);
        if (send(s, packet, sizeof(packet), 0) < sizeof(packet)) {
            printf("xmit: connection lost\n");
            exit(1);
        }
    }
}
    
