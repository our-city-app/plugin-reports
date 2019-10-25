import { ChangeDetectionStrategy, ChangeDetectorRef, Component, forwardRef, ViewEncapsulation } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { ThreePSettings } from '../../interfaces';


@Component({
  selector: 'r-3p-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  templateUrl: '3p-settings.component.html',
  providers: [{
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => ThreePSettingsComponent),
    multi: true,
  }],
})
export class ThreePSettingsComponent implements ControlValueAccessor {
  private onChange: Function;
  private onTouched: Function;
  settings: ThreePSettings | null = null;

  constructor(private changeDetectorRef: ChangeDetectorRef) {
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
  }

  writeValue(value?: ThreePSettings): void {
    if (value) {
      this.settings = value;
      this.changeDetectorRef.markForCheck();
    }
  }

  changed() {
    this.settings = { ...this.settings as ThreePSettings };
    this.onChange(this.settings);
    this.changeDetectorRef.markForCheck();
  }
}
