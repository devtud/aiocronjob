import React from 'react';
import './App.css';
import {ActionSheet, Badge, Button, List, NavBar, Tabs, Toast} from 'antd-mobile';

type JobStatus = "running" | "error" | "pending" | "done";

type Job = {
    name: string,
    last_status: JobStatus,
    crontab: string
}

interface State {
    jobs: Job[]
}


class JobsView extends React.Component<{}, State> {
    state: State = {
        jobs: [],
    };

    constructor(props: Readonly<{}>) {
        super(props);
        this.handleRefresh = this.handleRefresh.bind(this);
    }


    componentDidMount() {
        this.handleRefresh();
    }

    handleRefresh() {
        fetch(
            `${process.env.REACT_APP_API_URL}/api/jobs`,
        ).then((res: Response) => res.json())
            .then((data) => {
                console.log(data);
                this.setState({
                    jobs: data,
                });
            }).catch((reason => {
            Toast.offline(`${reason}`, 3);
        }));

    }

    static getStatusBadge(status: JobStatus) {

        let color;

        switch (status) {
            case "pending": {
                color = 'orange';
                break;
            }
            case "running": {
                color = 'green';
                break;
            }
            case "done": {
                color = '#000';
                break;
            }
            case "error": {
                color = 'red';
                break;
            }
            default: {
                color = 'grey';
            }
        }

        return <Badge text={status} style={{
            marginLeft: 12,
            padding: '0 3px',
            backgroundColor: '#fff',
            borderRadius: 2,
            color: color,
            border: `1px solid ${color}`,
        }}/>
    }

    doAction(jobName: string, action: "start" | "cancel") {
        return fetch(`${process.env.REACT_APP_API_URL}/api/jobs/${jobName}/${action}`);
    }

    showActionSheet = (job: Job) => {
        let buttons = [],
            action: "start" | "cancel";
        if (job.last_status === "running") {
            action = 'cancel';
            buttons.push("Stop job");
        } else {
            action = 'start';
            buttons.push("Start job");
        }
        buttons.push("Cancel");

        ActionSheet.showActionSheetWithOptions({
                options: buttons,
                cancelButtonIndex: buttons.length - 1,
                title: <span>{job.name} {JobsView.getStatusBadge(job.last_status)}</span>,
                message: <span>&#128339; {job.crontab}</span>,
                maskClosable: true,
            },
            (buttonIndex: number) => {
                if (buttonIndex === 0) {
                    this.doAction(job.name, action).then(
                        this.handleRefresh
                    ).catch(reason => {
                        console.error('oops', reason);
                    })
                }
            });
    }

    render() {
        const errors = this.state.jobs.filter(job => job.last_status === "error");
        const done = this.state.jobs.filter(job => job.last_status === "done");
        const running = this.state.jobs.filter(job => job.last_status === "running");

        const tabs = [
            {title: <Badge text={this.state.jobs.length}>All</Badge>},
            {title: <Badge text={running.length}>Running</Badge>},
            {title: <Badge text={errors.length}>Error</Badge>},
            {title: <Badge text={done.length}>Done</Badge>},
        ];

        const renderJobList = (jobs: Job[]) => {
            return (
                <List>
                    {jobs.map(job =>
                        <List.Item key={job.name}
                                   arrow="horizontal"
                                   onClick={() => this.showActionSheet(job)}
                        >
                            <span>{job.name}
                                {JobsView.getStatusBadge(job.last_status)}
                            </span>
                        </List.Item>
                    )}
                </List>
            )
        }


        return [
            <NavBar
                key="navbar"
                mode="light"
                rightContent={
                    <Button
                        icon={<img
                            src="https://gw.alipayobjects.com/zos/rmsportal/jBfVSpDwPbitsABtDDlB.svg"
                            alt=""/>}
                        inline size="small"
                        onClick={this.handleRefresh}
                    >
                        Refresh
                    </Button>
                }
            >Aiocronjob</NavBar>,

            <Tabs key="tabs"
                  tabs={tabs}
                  initialPage={1}
                  onChange={(tab, index) => {
                      console.log('onChange', index, tab);
                  }}
                  onTabClick={(tab, index) => {
                      console.log('onTabClick', index, tab);
                  }}
            >
                <div style={{height: '100%'}}>
                    {
                        this.state.jobs.length === 0 ?
                            <span>No jobs.</span> :
                            renderJobList(this.state.jobs)
                    }
                </div>
                <div style={{height: '100%'}}>
                    {
                        running.length === 0 ?
                            <span style={{margin: "auto"}}>No running jobs.</span> :
                            renderJobList(running)
                    }
                </div>
                <div style={{height: '100%'}}>
                    {errors.length === 0 ?
                        <span>No error jobs.</span> :
                        renderJobList(errors)}
                </div>
                <div style={{height: '100%'}}>
                    {done.length === 0 ? <span>No done jobs.</span> : renderJobList(done)}
                </div>
            </Tabs>
        ];
    }
}

function App() {
    return (
        <div className="App">

            <JobsView/>
        </div>
    );
}

export default App;
