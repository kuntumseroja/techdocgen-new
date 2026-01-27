import { Component, OnInit } from "@angular/core";
import { ApiService } from "./services/api.service";

@Component({
  selector: "app-root",
  templateUrl: "./app.component.html"
})
export class AppComponent implements OnInit {
  title = "TechDocGen Angular Example";
  status = "idle";

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getStatus().then((value) => {
      this.status = value;
    });
  }
}
