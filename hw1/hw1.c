#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define DEST_PORT 3700


int main(int argc, char* argv[]) {
    int port;
    char* hostname;
    char* nuId;
    
    if (argc == 5 && strcmp(argv[1], "-p") == 0) {
        port = atoi(argv[2]);
        hostname = argv[3];
        nuId = argv[4];    
    } else if (argc == 3) {
        port = DEST_PORT;
        hostname = argv[1];
        nuId = argv[2];
    } else {
        printf("\nWrong number of arguments!\n");
        return -1;
    }
    
    printf("\nport: %d, hostname: %s, nuId: %s\n", port, hostname, nuId);   
    return 0;
}
