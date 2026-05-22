using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace AKICinemaAdmin.Converters;

public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is true ? Visibility.Visible : Visibility.Collapsed;
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => value is Visibility.Visible;
}

public class InverseBoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is true ? Visibility.Collapsed : Visibility.Visible;
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => value is Visibility.Collapsed;
}

public class SeatStateToColorConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
    {
        return (value?.ToString()) switch
        {
            "selected" => new SolidColorBrush(Color.FromRgb(200, 16, 46)),
            "booked"   => new SolidColorBrush(Color.FromRgb(50, 50, 50)),
            _          => new SolidColorBrush(Color.FromRgb(42, 42, 42)),
        };
    }
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => Binding.DoNothing;
}

public class SeatStateToBorderConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
    {
        return (value?.ToString()) switch
        {
            "selected" => new SolidColorBrush(Color.FromRgb(232, 33, 62)),
            "booked"   => new SolidColorBrush(Color.FromRgb(40, 40, 40)),
            _          => new SolidColorBrush(Color.FromRgb(80, 80, 80)),
        };
    }
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => Binding.DoNothing;
}

public class SeatStateToForegroundConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
    {
        return (value?.ToString()) switch
        {
            "selected" => new SolidColorBrush(Colors.White),
            "booked"   => new SolidColorBrush(Color.FromRgb(60, 60, 60)),
            _          => new SolidColorBrush(Color.FromRgb(170, 170, 170)),
        };
    }
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => Binding.DoNothing;
}

public class SeatStateToEnabledConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value?.ToString() != "booked";
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => Binding.DoNothing;
}

public class VipToColorConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is true
            ? new SolidColorBrush(Color.FromRgb(212, 175, 55))
            : new SolidColorBrush(Color.FromRgb(200, 16, 46));
    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => Binding.DoNothing;
}
