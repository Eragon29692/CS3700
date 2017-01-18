#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>

#define DEST_PORT 3700

int getLength(char buffer[], int size) {
    int i = 0;
    int count = 0;
    while(buffer[i] != '\0' && i < size) {
        count++;
        i++;
    }
    return count;
}

void appendMessage(char *buffer, char *message, int size) {
    int i = 0;
    int messageLength = getLength(message, size);

    while(*(buffer + i) != '\0' && i < size - 1) {
        if (length + i > size) {
            printf("message too long");
            exit(0);
        }
        *(message + length + i) = *(buffer + i) 
    }
}

int main(int argc, char* argv[]) {
    int port;
    char hostname[100] = "";
    char nuId[10] = "";
    struct hostent *host;

    if (argc == 5 && strcmp(argv[1], "-p") == 0) {
        port = atoi(argv[2]);
        strcpy(hostname, argv[3]);
        strcpy(nuId, argv[4]);    
    } else if (argc == 3) {
        port = DEST_PORT;
        strcpy(hostname, argv[1]);
        strcpy(nuId, argv[2]);
    } else {
        printf("\nWrong number of arguments!\n");
        return -1;
    }
    
    // printf("\nport: %d, hostname: %s, nuId: %s\n", port, hostname, nuId);

    int sockfd;
    struct sockaddr_in dest_addr;
    char messageBuff[64] = "";
    char buffer[64] = "";

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        printf("\nCannot open socket");
        return -1;
    }
    host = gethostbyname(hostname);
    if (host == NULL) {
        printf("\nCan't get hostname's IP\n");
        return -1;
    }

    dest_addr.sin_family = AF_INET;          // host byte order
    dest_addr.sin_port = htons(port);   // short, network byte order
    //dest_addr.sin_addr.s_addr = inet_addr(host);
    //memset(&(dest_addr.sin_zero), '\0', 8);  // zero the rest of the struct
    memcpy(&dest_addr.sin_addr.s_addr, host->h_addr, host->h_length);

    
    if (connect(sockfd, (struct sockaddr *)&dest_addr, sizeof(struct sockaddr)) < 0) {
        printf("\nCannot open socket");
        return -1;
    } else {
        if (recv(sockfd, buffer, 64, 0) >= 0) { 
         
        }
        while(1) {
            if (recv(sockfd, buffer, 64, 0) >= 0) {
                int i = 0;
                while(buffer[i] != '\0')
                printf("\nmessage: %s\n", buffer);
            }
        }
    }
    return 0;
}
