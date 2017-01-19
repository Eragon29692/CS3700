#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>

#define DEST_PORT 3700
#define MAX_SIZE 64

int getLength(char buffer[], int size) {
    int i = 0;
    int count = 0;
    while(buffer[i] != '\0' && i < size) {
        count++;
        i++;
    }
    return count;
}

void appendString(char *buffer, char *message, int size) {
    int i = 0;
    int length = getLength(message, size);

    while(*(buffer + i) != '\0' && i < size - 1) {
        if (length + i < size - 1) {
            *(message + length + i) = *(buffer + i);
        } else {
            printf("too long: %d", getLength(message, size));
            exit(0);
        }
        i++;
    }
    *(message + length + i) = '\0';
}

int checkForNewline(char message[], int size) {
    int i = 0;
    while(i < size) {
        if (message[i] == '\n') {
            return 1;
        }
        i++;
    }
    return 0;
}

void addNewline(char *buffer) {
    *(buffer + getLength(buffer, MAX_SIZE)) = '\n';
}

void resetArray(char *message, int size) {
    int i = 0;
    while(i < size) {
        *(message + i) = '\0';
        i++;
    }
}

void getSendString(char *result, char *sendString) {
    int i = 0; //sine INFO  is 5 spaces to the numbers
    while(sendString[i] != '\0') {
        *(result + i) = *(sendString + i);
        i++;
       
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
    char messageBuff[MAX_SIZE] = "";
    char buffer[MAX_SIZE] = "";
    char sendInfo[MAX_SIZE] = "";
    int looping = 1; //flag to stop while loops
    

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

    dest_addr.sin_family = AF_INET;     // host byte order
    dest_addr.sin_port = htons(port);   // short, network byte order
    memcpy(&dest_addr.sin_addr.s_addr, host->h_addr, host->h_length);

    
    if (connect(sockfd, (struct sockaddr *)&dest_addr, sizeof(struct sockaddr)) < 0) {
        printf("\nCannot open socket");
        return -1;
    } else {
        //wait for HELLO
        while(looping) { 
            if (recv(sockfd, buffer, MAX_SIZE, 0) >= 0) { 
                appendString(buffer, messageBuff, MAX_SIZE);
                if(checkForNewline(messageBuff, MAX_SIZE) != 0) {
                    looping = 0;
                    printf("\nReceive: %s\n", messageBuff);
                    resetArray(messageBuff, MAX_SIZE); //reset messageBuff

                    char sendString[] = "IAM ";
                    appendString(nuId, sendString, MAX_SIZE);
                    
                    char result[getLength(sendString, MAX_SIZE)];
                    getSendString(result, sendString);
                    
                    addNewline(result);
                    send(sockfd, result, MAX_SIZE, 0);
                    printf("\nSend: %s\n", result);
                    send(sockfd, result, MAX_SIZE, 0);
                }
            }
        }
        looping = 1; 
        //respone to INFOs
        while(looping) {
            if (recv(sockfd, buffer, MAX_SIZE, 0) >= 0) {
                printf("\nbuffer: %s", buffer);
                printf("\nmessage: %s", messageBuff);
                appendString(buffer, messageBuff, MAX_SIZE);
                if(checkForNewline(messageBuff, MAX_SIZE) != 0) {
                    printf("\nReceive: %s\n", messageBuff);
                    if (messageBuff[0]=='N' && messageBuff[1]=='U' && messageBuff[2]=='L' && messageBuff[3]=='L') {
                        //NULL case
                        printf("NUll here");
                        resetArray(messageBuff, MAX_SIZE); //reset messageBuff
                    } else if (messageBuff[0]=='K' && messageBuff[1]=='E' && messageBuff[2]=='Y') {
                        //KEY case
                        printf("\nDone");
                        looping = 0;
                    } else { 
                        //REPLY case
                        char sendString[] = "REPLY ";
                        appendString((messageBuff + 5), sendString, MAX_SIZE);
                        
                        resetArray(messageBuff, MAX_SIZE); //reset messageBuff
                        printf("\nSend: %s\n", sendString);
                        char result[getLength(sendString, MAX_SIZE) + 1];
                        getSendString(result, sendString);
                        //printf("hhhh:%s", result);
                        addNewline(result);
                        send(sockfd, result, MAX_SIZE, 0);
                    }
                }
            }
        }
    }
    return 0;
}
