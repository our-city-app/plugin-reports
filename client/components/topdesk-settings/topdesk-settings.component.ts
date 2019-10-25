import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  forwardRef,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { NameId, TopdeskData, TopdeskSettings } from '../../interfaces';

@Component({
  selector: 'r-topdesk-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: 'topdesk-settings.component.html',
  styles: [`.r-topdesk-settings {
      width: 100%;
      display: flex;
      flex-direction: column;
  }`],
  providers: [{
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => TopdeskSettingsComponent),
    multi: true,
  }],
})
export class TopdeskSettingsComponent implements ControlValueAccessor, OnChanges {
  hasData = false;
  categories: { [ key: string ]: NameId[] } = {};

  @Input() data: TopdeskData | null;
  @Output() loadData = new EventEmitter<TopdeskSettings>();

  private onChange: Function;
  private onTouched: Function;
  settings: TopdeskSettings | null = null;

  constructor(private changeDetectorRef: ChangeDetectorRef) {
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.data && changes.data.currentValue && this.data) {
      this.hasData = true;
      this.categories = {};
      for (const category of this.data.subCategories) {
        if (category.category.id in this.categories) {
          this.categories[ category.category.id ].push({ id: category.id, name: category.name });
        } else {
          this.categories[ category.category.id ] = [{ id: category.id, name: category.name }];
        }
      }
    }
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
  }

  writeValue(value?: TopdeskSettings): void {
    if (value) {
      this.settings = value;
      this.loadDataIfNeeded();
      this.changeDetectorRef.markForCheck();
    }
  }

  changed() {
    this.settings = { ...this.settings as TopdeskSettings };
    this.onChange(this.settings);
    this.changeDetectorRef.markForCheck();
  }

  loadDataIfNeeded() {
    if (this.settings && this.settings.api_url && this.settings.username && this.settings.password && !this.hasData) {
      this.loadData.emit(this.settings);
    }
  }

  categoryChanged() {
    (this.settings as TopdeskSettings).sub_category_id = null;
    this.changed();
  }
}
