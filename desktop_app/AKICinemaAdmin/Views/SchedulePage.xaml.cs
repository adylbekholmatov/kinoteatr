using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using AKICinemaAdmin.Models;

namespace AKICinemaAdmin.Views;

public partial class SchedulePage : Page
{
    public event Action<Screening>? ScreeningSelected;
    public event Action<DateTime, int>? ScreeningsLoaded;

    private DateTime _selectedDate = DateTime.Today;
    private List<Screening> _screenings = new();
    private bool _isLoading = false;

    public SchedulePage()
    {
        InitializeComponent();
        // Suppress event while setting initial date
        DatePicker.SelectedDateChanged -= DatePicker_SelectedDateChanged;
        DatePicker.SelectedDate = _selectedDate;
        DatePicker.SelectedDateChanged += DatePicker_SelectedDateChanged;

        BuildDateStrip();
        SubtitleLabel.Text = $"Сегодня, {DateTime.Today:dd MMMM yyyy}";
        _ = LoadScreeningsAsync();
    }

    private void BuildDateStrip()
    {
        DateStrip.Children.Clear();
        for (int i = 0; i < 7; i++)
        {
            var d = DateTime.Today.AddDays(i);
            var btn = new Button
            {
                Width = 64,
                Height = 64,
                Margin = new Thickness(4, 0, 4, 0),
                Cursor = Cursors.Hand,
                Tag = d,
                Template = CreateDateButtonTemplate(d, d.Date == _selectedDate.Date)
            };
            btn.Click += (s, e) =>
            {
                _selectedDate = (DateTime)((Button)s).Tag;
                BuildDateStrip();
                DatePicker.SelectedDate = _selectedDate; // triggers DatePicker_SelectedDateChanged → load
            };
            DateStrip.Children.Add(btn);
        }
    }

    private ControlTemplate CreateDateButtonTemplate(DateTime d, bool isActive)
    {
        var template = new ControlTemplate(typeof(Button));
        var factory = new FrameworkElementFactory(typeof(Border));
        factory.SetValue(Border.CornerRadiusProperty, new CornerRadius(8));
        factory.SetValue(Border.BackgroundProperty,
            isActive ? new SolidColorBrush(Color.FromRgb(200, 16, 46))
                     : new SolidColorBrush(Color.FromRgb(34, 34, 34)));
        factory.SetValue(Border.BorderBrushProperty,
            isActive ? new SolidColorBrush(Color.FromRgb(232, 33, 62))
                     : new SolidColorBrush(Color.FromRgb(46, 46, 46)));
        factory.SetValue(Border.BorderThicknessProperty, new Thickness(1));
        factory.SetValue(Border.CursorProperty, Cursors.Hand);

        var sp = new FrameworkElementFactory(typeof(StackPanel));
        sp.SetValue(StackPanel.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        sp.SetValue(StackPanel.VerticalAlignmentProperty, VerticalAlignment.Center);

        var dayName = new FrameworkElementFactory(typeof(TextBlock));
        dayName.SetValue(TextBlock.TextProperty,
            d.ToString("ddd", new System.Globalization.CultureInfo("ru-RU")).ToUpper());
        dayName.SetValue(TextBlock.FontSizeProperty, 9.0);
        dayName.SetValue(TextBlock.ForegroundProperty,
            isActive ? new SolidColorBrush(Colors.White) : new SolidColorBrush(Color.FromRgb(136, 136, 136)));
        dayName.SetValue(TextBlock.HorizontalAlignmentProperty, HorizontalAlignment.Center);

        var dayNum = new FrameworkElementFactory(typeof(TextBlock));
        dayNum.SetValue(TextBlock.TextProperty, d.Day.ToString());
        dayNum.SetValue(TextBlock.FontSizeProperty, 20.0);
        dayNum.SetValue(TextBlock.FontWeightProperty, FontWeights.Bold);
        dayNum.SetValue(TextBlock.ForegroundProperty, new SolidColorBrush(Colors.White));
        dayNum.SetValue(TextBlock.HorizontalAlignmentProperty, HorizontalAlignment.Center);

        sp.AppendChild(dayName);
        sp.AppendChild(dayNum);
        factory.AppendChild(sp);
        template.VisualTree = factory;
        return template;
    }

    private void DatePicker_SelectedDateChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (DatePicker.SelectedDate.HasValue)
        {
            _selectedDate = DatePicker.SelectedDate.Value;
            BuildDateStrip();
            _ = LoadScreeningsAsync();
        }
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e)
        => _ = LoadScreeningsAsync();

    private async System.Threading.Tasks.Task LoadScreeningsAsync()
    {
        if (_isLoading) return;
        _isLoading = true;

        LoadingPanel.Visibility = Visibility.Visible;
        EmptyPanel.Visibility   = Visibility.Collapsed;
        ListScroll.Visibility   = Visibility.Collapsed;
        ScreeningsList.Children.Clear();

        _screenings = await App.Api.GetScreeningsAsync(_selectedDate);
        ScreeningsLoaded?.Invoke(_selectedDate, _screenings.Count);
        SubtitleLabel.Text = $"{_selectedDate:dd MMMM yyyy} — {_screenings.Count} сеансов";

        LoadingPanel.Visibility = Visibility.Collapsed;

        if (_screenings.Count == 0)
        {
            EmptyPanel.Visibility = Visibility.Visible;
            _isLoading = false;
            return;
        }

        ListScroll.Visibility = Visibility.Visible;
        foreach (var s in _screenings)
            ScreeningsList.Children.Add(CreateScreeningCard(s));

        _isLoading = false;
    }

    private Border CreateScreeningCard(Screening s)
    {
        var isVip = s.Hall.IsVip;
        var accentColor = isVip
            ? Color.FromRgb(212, 175, 55)
            : Color.FromRgb(200, 16, 46);

        var card = new Border
        {
            Background = new SolidColorBrush(Color.FromRgb(26, 26, 26)),
            BorderBrush = new SolidColorBrush(Color.FromRgb(46, 46, 46)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(10),
            Margin = new Thickness(0, 0, 0, 10),
            Padding = new Thickness(20, 16, 20, 16),
            Cursor = Cursors.Hand,
        };

        card.MouseEnter += (s2, e) =>
            card.BorderBrush = new SolidColorBrush(accentColor);
        card.MouseLeave += (s2, e) =>
            card.BorderBrush = new SolidColorBrush(Color.FromRgb(46, 46, 46));
        card.MouseLeftButtonUp += (s2, e) =>
            ScreeningSelected?.Invoke(s);

        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        // Left: movie info
        var leftPanel = new StackPanel { VerticalAlignment = VerticalAlignment.Center };

        var titleRow = new WrapPanel { Margin = new Thickness(0, 0, 0, 6) };

        var timeBlock = new TextBlock
        {
            Text = s.TimeDisplay,
            FontSize = 22,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(accentColor),
            Margin = new Thickness(0, 0, 14, 0),
            VerticalAlignment = VerticalAlignment.Center
        };

        var titleBlock = new TextBlock
        {
            Text = s.Movie.TitleRu,
            FontSize = 16,
            FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(Colors.White),
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 10, 0)
        };

        var ageBadge = new Border
        {
            Background = new SolidColorBrush(Color.FromRgb(200, 16, 46)),
            CornerRadius = new CornerRadius(3),
            Padding = new Thickness(6, 2, 6, 2),
            VerticalAlignment = VerticalAlignment.Center
        };
        ageBadge.Child = new TextBlock
        {
            Text = s.Movie.AgeRating,
            FontSize = 10,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(Colors.White)
        };

        titleRow.Children.Add(timeBlock);
        titleRow.Children.Add(titleBlock);
        titleRow.Children.Add(ageBadge);

        if (isVip)
        {
            var vipBadge = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(30, 212, 175, 55)),
                BorderBrush = new SolidColorBrush(Color.FromRgb(212, 175, 55)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(3),
                Padding = new Thickness(6, 2, 6, 2),
                Margin = new Thickness(8, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center
            };
            vipBadge.Child = new TextBlock
            {
                Text = "VIP",
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush(Color.FromRgb(212, 175, 55))
            };
            titleRow.Children.Add(vipBadge);
        }

        var metaRow = new WrapPanel();
        void AddMeta(string text)
        {
            metaRow.Children.Add(new TextBlock
            {
                Text = text,
                Foreground = new SolidColorBrush(Color.FromRgb(136, 136, 136)),
                FontSize = 12,
                Margin = new Thickness(0, 0, 20, 0)
            });
        }

        AddMeta($"🏛 {s.Hall.Name}");
        AddMeta($"⏱ {s.Movie.DurationDisplay}");
        AddMeta($"🎟 Свободно: {s.AvailableSeats} мест");

        leftPanel.Children.Add(titleRow);
        leftPanel.Children.Add(metaRow);
        Grid.SetColumn(leftPanel, 0);

        // Right: price & button
        var rightPanel = new StackPanel
        {
            VerticalAlignment = VerticalAlignment.Center,
            HorizontalAlignment = HorizontalAlignment.Right,
            MinWidth = 140
        };

        rightPanel.Children.Add(new TextBlock
        {
            Text = $"{s.PriceDecimal:0} сом",
            FontSize = 20,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(accentColor),
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, 8)
        });

        var buyBtn = new Button
        {
            Content = "Продать билет →",
            Style = (Style)Application.Current.Resources["RedButtonStyle"],
            Padding = new Thickness(16, 8, 16, 8),
            FontSize = 12,
            IsEnabled = s.AvailableSeats > 0
        };
        buyBtn.Click += (s2, e) => ScreeningSelected?.Invoke(s);

        if (isVip)
        {
            buyBtn.Background = new SolidColorBrush(Color.FromRgb(180, 140, 30));
        }

        rightPanel.Children.Add(buyBtn);
        Grid.SetColumn(rightPanel, 1);

        grid.Children.Add(leftPanel);
        grid.Children.Add(rightPanel);
        card.Child = grid;
        return card;
    }
}
