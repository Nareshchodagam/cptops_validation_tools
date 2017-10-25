package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

var relam string

type healthStatus struct {
	AllPassed bool `json:"all-passed"`
}

func main() {

	Hosts := flag.String("hosts", "", "Hosts to get Cluster Health")
	flag.Parse()

	// Verify user has passed command line argument
	if *Hosts == "" {
		flag.PrintDefaults()
		os.Exit(1)
	}

	hostlist := strings.Split(*Hosts, ",") // Split comma separated string to array

	output := new(healthStatus)
	hostURL := "http://%s:8080/health" // Url to connect
	c := &http.Client{
		Timeout: 35 * time.Second,
	}

	// Checking host relam
	if strings.Contains(hostlist[0], "prd") || strings.Contains(hostlist[0], "crd") {
		relam = ".eng.sfdc.net"
	} else {
		relam = ".ops.sfdc.net"
	}

	// Checking if Cluster health is OK
	for _, host := range hostlist {
		host = host + relam
		fr := func() error {
			resp, err := c.Get(fmt.Sprintf(hostURL, host))
			if err != nil {
				log.Printf("cannot connect to %s %s \n", host, err)
				return err
			}
			defer resp.Body.Close()
			rawBody, err := ioutil.ReadAll(resp.Body)
			if err != nil {
				log.Printf(" %s \n", err)
				return err
			}
			err = json.Unmarshal(rawBody, output)
			if err != nil {
				log.Printf("%s \n", err)
				return err
			}
			return nil

		}()
		if fr == nil {
			break
		}
	}
	if output.AllPassed {
		log.Printf("Cluster Health is OK. \n")
		os.Exit(0)
	} else {
		log.Printf("Cluster Health Critical. \n")
		os.Exit(1)
	}
}
